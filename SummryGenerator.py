import sys
import json
import pandas as pd
import datetime
import argparse

"""
Description
-----------
Generates xlsx report showing approx income from bank transaction list.
Considers ICICI and OBC bank statements to find actual income.

Parameters
----------
ICFile - str - Full file name(with path) for ICICI bank statement file
OBCFile - str- Full file name(with path) for OBC bank statement file

"""

def user_input(s):
    if sys.version_info[0] == 3:
        retStr = input(s)
    else:
        retStr = raw_input(s)
    return retStr

def cleanICFile(dfI):
    dfI.dropna(axis=1,how='all',inplace=True)
    dfI.dropna(axis=0,how='all',inplace=True)
    dfI.dropna(axis=1,thresh=10,inplace=True)
    dfI.dropna(axis=0,thresh=5,inplace=True)
    # dfI.columns=list(dfI.iloc[0])
    dfI.drop(dfI.index[0],axis=0,inplace=True)
    dfI.reset_index(inplace=True)
    dfI.drop(columns='index',inplace=True)
    print(dfI.columns)
    dfI=dfI.astype({"Withdrawal Amount ( )":float,"Deposit Amount ( )":float,"Balance ( )":float})
    dfI['Value Date']=pd.to_datetime(dfI['Value Date'], format="%d/%m/%Y")
    dfI['Transaction Date']=pd.to_datetime(dfI['Transaction Date'], format="%d/%m/%Y")
    return dfI

def cleanOBCFile(dfO):
    dfO.dropna(axis=1,how='all',inplace=True)
    dfO.dropna(axis=0,how='all',inplace=True)
    dfO.dropna(axis=1,how='any',thresh=10,inplace=True)
    dfO.dropna(axis=0,how='any',thresh=4,inplace=True)
    # dfO.columns=list(dfO.iloc[0])
    dfO.drop(dfO.index[0],axis=0,inplace=True)
    dfO.reset_index(inplace=True)
    dfO.drop(columns='index',inplace=True)
    dfO.replace({'Deposit':r',','Withdrawal':r',','Balance':r',|Cr\.|Dr\.'},{"Deposit":'',"Withdrawal":'',"Balance":''},regex=True,inplace=True)
    dfO.fillna(0,inplace=True)
    dfO=dfO.astype({"Deposit":float,"Withdrawal":float,"Balance":float})
    dfO['Transaction Date']=pd.to_datetime(dfO['Transaction Date'], format="%d/%m/%Y")
    return dfO

parser = argparse.ArgumentParser(description='Input Arguments for SummaryGenerator')
parser.add_argument('--ic',dest='ICFile',help='ICICI Excel file location')
parser.add_argument('--obc',dest='OBCFile',help='OBC Excel file location')
parser.add_argument('--out',dest='outputFile',help='Output xlsx file name')

args = parser.parse_args()
args = vars(args)

ICFile = ''
OBCFile = ''
ICFileMade = False
OBCFileMade = False

if args['ICFile']:
    ICFile = args['ICFile']
# else:
#     ICFile = user_input("ICICI File:")
if args['OBCFile']:
    OBCFile = args['OBCFile']
# else:
#     OBCFile = user_input("OBC File:")
if args['outputFile']:
    outputFile = args['outputFile']
else:
    outputFile = user_input("Output xlsx file:")

# --------- ICICI file
if args['ICFile']:
    dfI=pd.read_excel(ICFile)
    print(dfI.columns)
    # Data Cleansing
    dfI=cleanICFile(dfI)
    # Replace remarks separators with / and split remarks into max 3 columns
    dfI['Transaction Remarks']=dfI['Transaction Remarks'].str.replace('-','/')
    dfI['Transaction Remarks']=dfI['Transaction Remarks'].str.replace(':','/')
    expnd_remarks=dfI['Transaction Remarks'].str.split('/',n=3,expand=True)
    expnd_remarks.columns=['c1','c2','c3','c4']
    # Join expanded remarks df with original dfIC
    dfIC=pd.concat([dfI,expnd_remarks],axis=1)
    # Filter out records where deposit is greater than 0
    dfICr=dfIC.loc[dfIC['Deposit Amount ( )']>0]
    # Filter out records which are NEFT or ACH
    dfICr_1=dfICr.loc[(dfICr['c1'] == 'NEFT') | ( dfICr['c1']== 'ACH')]
    ICFileMade = True

# --------- OBC File
if args['OBCFile']:
    dfO=pd.read_excel(OBCFile)
    # Data Cleansing
    dfO=cleanOBCFile(dfO)
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
    OBCFileMade = True

# Save to Excel
if ICFileMade or OBCFileMade:
    writer=pd.ExcelWriter(outputFile)
if ICFileMade:
    dfIC.to_excel(writer, 'ICICI')
    dfICr.to_excel(writer,'IC_NetCredit')
    dfICr_1.to_excel(writer,'IC_NEFT_ACH')
if OBCFileMade:
    dfO.to_excel(writer, 'PNB')
    dfOCr.to_excel(writer,'OBC_NetCredit')
    dfOCr_1.to_excel(writer,'OBC_nonSweep')
    dfSweep.to_excel(writer,'OBC_FDInt')
if ICFileMade or OBCFileMade:
    writer.close()