from __future__ import annotations

import pandas as pd
import datetime
import argparse
import io

"""
Description
-----------s
Generates xlsx report showing approx income from bank transaction list.
Considers ICICI and OBC bank statements to find actual income.

Parameters
----------
ICFile - str - Full file name(with path) for ICICI bank statement file
OBCFile - str- Full file name(with path) for OBC bank statement file

"""

def clean_ic_file(dfI: pd.DataFrame):
    dfI.dropna(axis=1,how='all',inplace=True)
    dfI.dropna(axis=0,how='all',inplace=True)
    dfI.dropna(axis=1,thresh=10,inplace=True)
    dfI.dropna(axis=0,thresh=5,inplace=True)
    # dfI.columns=list(dfI.iloc[0])
    # dfI.drop(dfI.index[0],axis=0,inplace=True)
    dfI.reset_index(inplace=True)
    dfI.drop(columns='index',inplace=True)
    dfI=dfI.astype({"Withdrawal Amount (INR )":float,"Deposit Amount (INR )":float,"Balance (INR )":float})
    dfI['Value Date']=pd.to_datetime(dfI['Value Date'], format="%d/%m/%Y")
    dfI['Transaction Date']=pd.to_datetime(dfI['Transaction Date'], format="%d/%m/%Y")
    return dfI

def clean_pnb_file(dfO: pd.DataFrame):
    dfO.dropna(axis=1,how='all',inplace=True)
    dfO.dropna(axis=0,how='all',inplace=True)
    dfO.dropna(axis=1,thresh=3,inplace=True)
    dfO.dropna(axis=0,thresh=4,inplace=True)
    # dfO.columns=list(dfO.iloc[0])
    # dfO.drop(dfO.index[0],axis=0,inplace=True)
    dfO.reset_index(inplace=True)
    dfO.drop(columns='index',inplace=True)
    dfO.replace({'Deposit':r',','Withdrawal':r',','Balance':r',|Cr\.|Dr\.'},{"Deposit":'',"Withdrawal":'',"Balance":''},regex=True,inplace=True)
    dfO.fillna(0,inplace=True)
    dfO=dfO.astype({"Deposit":float,"Withdrawal":float,"Balance":float})
    dfO['Transaction Date']=pd.to_datetime(dfO['Transaction Date'], format="%d/%m/%Y")
    return dfO

def process_icici(files: list[str]) -> dict[str, pd.DataFrame]:
    dfs_full: list[pd.DataFrame] = []
    dfs_cr: list[pd.DataFrame] = []
    dfs_cr_1: list[pd.DataFrame] = []

    for file in files:
        dfI=pd.read_excel(file)
        # Data Cleansing
        dfI=clean_ic_file(dfI)
        # Replace remarks separators with / and split remarks into max 3 columns
        dfI['Transaction Remarks']=dfI['Transaction Remarks'].str.replace('-','/')
        dfI['Transaction Remarks']=dfI['Transaction Remarks'].str.replace(':','/')
        expnd_remarks=dfI['Transaction Remarks'].str.split('/',n=3,expand=True)
        expnd_remarks.columns=['c1','c2','c3','c4']
        # Join expanded remarks df with original dfIC
        dfIC=pd.concat([dfI,expnd_remarks],axis=1)
        # Filter out records where deposit is greater than 0
        dfICr=dfIC.loc[dfIC['Deposit Amount (INR )']>0]
        # Filter out records which are NEFT or ACH
        dfICr_1=dfICr.loc[(dfICr['c1'] == 'NEFT') | ( dfICr['c1']== 'ACH')]

        dfs_full.append(dfIC)
        dfs_cr.append(dfICr)
        dfs_cr_1.append(dfICr_1)
    return {
        "ICICI": pd.concat(dfs_full),
        "IC_NetCredit": pd.concat(dfs_cr),
        "IC_NEFT_ACH": pd.concat(dfs_cr_1),
    }

def process_pnb(files: list[str]) -> dict[str, pd.DataFrame]:
    dfs_full: list[pd.DataFrame] = []
    dfs_cr: list[pd.DataFrame] = []
    dfs_cr_1: list[pd.DataFrame] = []
    dfs_sweep: list[pd.DataFrame] = []

    for file in files:
        dfO=pd.read_excel(file)
        # Data Cleansing
        dfO=clean_pnb_file(dfO)
        # dfO=dfO.drop(columns=['net','int'])
        # Replace narration separators with /
        dfO['Narration']=dfO['Narration'].str.replace(':','/',2)
        # Filter out records where credit is greater than 0
        dfOCr=dfO.loc[dfO['Deposit']>0]
        # Exclude records of SWEEP transactions
        dfOCr_1=dfOCr.loc[~dfOCr['Narration'].str.lower().str.contains('sweep|proceeds|tax|repayment credit',regex=True)]
        # Separate out all Sweep Credit transactions
        dfSweep=dfOCr.loc[dfOCr['Narration'].str.lower().str.contains('tax',regex=True)].copy()
        # Logic for calculating approx FD Interest
        lm1= lambda x : int(x/5000)*5000
        # Calculates the round off Principal value for interest calculation
        lm2= lambda x : 5000*int(x/1.028/5000*10+0.5)/10
        # dfSweep['FDInt']=dfSweep['Deposit']-dfSweep['Deposit'].apply(lm2)

        dfs_full.append(dfO)
        dfs_cr.append(dfOCr)
        dfs_cr_1.append(dfOCr_1)
        dfs_sweep.append(dfSweep)

    return {
        "PNB": pd.concat(dfs_full),
        "OBC_NetCredit": pd.concat(dfs_cr),
        "OBC_nonSweep": pd.concat(dfs_cr_1),
        "OBC_FDInt": pd.concat(dfs_sweep),
    }

def process_cc(files: list[str]) -> dict[str, pd.DataFrame]:
    # "Date","Sr.No.","Transaction Details","Reward Point Header","Intl.Amount","Amount(in Rs)","BillingAmountSign"

    dfs_full: list[pd.DataFrame] = []

    for file in files:
        with open(file) as f:
            fc = f.read()

        final_lines = []
        for l in fc.split("\n"):
            if len(l.split('","')) > 5:
                final_lines.append(l)

        df = pd.read_csv(io.StringIO("\n".join(final_lines)))
        df['Date'] = pd.to_datetime(df['Date'], format="%d/%m/%Y")
        amount_col =  [i for i, col in enumerate(df.columns) if col.startswith("Amount")]

        loc = amount_col[0] + 1 if amount_col else len(df.columns) - 1
        df.insert(loc, "Cat", "")
        dfs_full.append(df)

    return {"out": pd.concat(dfs_full, ignore_index=True)}

def main():
    parser = argparse.ArgumentParser(description='Input Arguments for SummaryGenerator')
    parser.add_argument("files", nargs='+')
    parser.add_argument('--ic', action='store_true', help='ICICI mode')
    parser.add_argument('--pnb', action='store_true', help='PNB mode')
    parser.add_argument('--cc', action='store_true', help='Credit card')
    parser.add_argument('--out', type=str, required=True, help='Output xlsx file name')

    args = parser.parse_args()

    sheet_to_dfs: dict[str, pd.DataFrame] = {}
    if args.ic:
        sheet_to_dfs = process_icici(args.files)
    elif args.pnb:
        sheet_to_dfs = process_pnb(args.files)
    elif args.cc:
        sheet_to_dfs = process_cc(args.files)


    with pd.ExcelWriter(args.out) as writer:
        for sheet_name, df in sheet_to_dfs.items():
            df.to_excel(writer, sheet_name=sheet_name)

if __name__ == "__main__":
    main()