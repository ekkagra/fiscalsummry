import sys
import pandas as pd

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

if len(sys.argv) != 3:
	ICFile = user_input("ICICI File:")
	OBCFile = user_input("OBC File:")
else:
	ICFile=sys.argv[1]
	OBCFile=sys.argv[2]

# ICICI file
dfI=pd.read_excel(ICFile)
# Replace remarks separators with / and split remarks into max 3 columns
dfI['Transaction Remarks']=dfI['Transaction Remarks'].str.replace('-','/')
dfI['Transaction Remarks']=dfI['Transaction Remarks'].str.replace(':','/')
expnd_remarks=dfI['Transaction Remarks'].str.split('/',3,expand=True)
expnd_remarks.columns=['c1','c2','c3','c4']
# Join expanded remarks df with original dfIC
dfIC=pd.concat([dfI,expnd_remarks],axis=1)
# Filter out records where deposit is greater than 0
dfICr=dfIC.loc[dfIC['Deposit Amount (INR )']>0]
# Filter out records which are NEFT or ACH  
dfICr_1=dfICr.loc[(dfICr['c1'] == 'NEFT') | ( dfICr['c1']== 'ACH')]

# OBC File
dfO=pd.read_excel(OBCFile)
# dfO=dfO.drop(columns=['net','int'])
# Replace narration separators with / 
dfO['Narration']=dfO['Narration'].str.replace(':','/',2)
# Filter out records where credit is greater than 0
dfOCr=dfO.loc[dfO['Credit']>0]
# Exclude records of SWEEP transactions
dfOCr_1=dfOCr.loc[~dfOCr['Narration'].str.lower().str.contains('sweep|proceeds',regex=True)]
# Separate out all Sweep Credit transactions
dfSweep=dfOCr.loc[dfOCr['Narration'].str.lower().str.contains('sweep|proceeds',regex=True)].copy()
# Logic for calculating approx FD Interest
lm1= lambda x : int(x/5000)*5000
dfSweep['FDInt']=dfSweep['Credit']-dfSweep['Credit'].apply(lm1)

# Save to Excel
writer=pd.ExcelWriter('FiscalSummry.xlsx')
dfICr.to_excel(writer,'IC_NetCredit')
dfICr_1.to_excel(writer,'IC_NEFT_ACH')
dfOCr.to_excel(writer,'OBC_NetCredit')
dfOCr_1.to_excel(writer,'OBC_nonSweep')
dfSweep.to_excel(writer,'OBC_FDInt')
writer.save()