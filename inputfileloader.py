import numpy as np
import pandas as pd
import re

# desc_value_length = 16

# standardize vendor description by
#    - UPCASE 
#    - convert any non-alphnumeric character, eq '&', and character sequences, eq '& (', to single space
#    - Pad or trim to outputlength
def createvendorgroupbyvalue(inputrow, descfieldname, outputlength):

    # create format string like {:16.16} that trims output to same length
    formatstring = '{{:{0}.{0}}}'.format(outputlength)

    inputname = inputrow[descfieldname]

    if isinstance(inputname, str):
        # convert non-alphanumeric characters to space. 
        # if multiple non-alphanumeric characters next to each other, this converts them to 1 space.
        inputnameonlyalphnumeric = re.sub('[^0-9a-zA-Z]+', ' ', inputname)

        return formatstring.format(inputnameonlyalphnumeric.upper())

    else:
        return formatstring.format('NO DESCRIPTION!!!')


def load_concur_report(concur_report_path: str, desc_field_name: str, desc_value_length: int) -> pd.DataFrame:

    # Load Concur report
    concurreport = pd.read_excel(
        concur_report_path,
        0, # Read the first worksheet
        0, # Header is on row 0 (row 1 in Excel's 1base count)
        )

    # Constructed the DescValue column using the createvendorgroupbyvalue function
    concurreport['DescValue'] = concurreport.apply(
        createvendorgroupbyvalue, 
        args=(desc_field_name, desc_value_length, ), 
        axis=1,
        )
    

   # Select only Corporate Card transaction (no cash...)
    concurreport = concurreport[ concurreport['Payment Type'] == 'US American Express Corporate Card' ] 
    return concurreport


def load_amex_tran(amex_tran_path: str, desc_field_name: str, desc_value_length: int) -> pd.DataFrame:

    # Load Amex Transaction 
    amextran = pd.read_excel(
        amex_tran_path,
        0,   # Read the first worksheet which should be the "Transaction Details" sheet
        6    # Header is on row 6 (row 7 in Excel 1base cout)
        )
    
    amextran_no_remittance = amextran[ amextran[desc_field_name].str.startswith('CORPORATE REMITTANCE') == False ] 

    # converting Date colum from plain Object to Date for joining to Concur Report DateFrame
    amextran_no_remittance['Date'] = pd.to_datetime(amextran_no_remittance['Date'])

    # Constructed the DescValue column using the createvendorgroupbyvalue function
    amextran_no_remittance['DescValue'] = amextran_no_remittance.apply(
        createvendorgroupbyvalue, 
        args=(desc_field_name, desc_value_length, ), 
        axis=1,
        )
    
    return amextran_no_remittance

def cluster_tran_entries(
        transactions: pd.DataFrame, 
        desc_column_name: str,
        date_column_name: str,
        amount_column_name: str,
        date_cluster_tolerance: str,) -> pd.DataFrame:
    # Create cluster of expenses for a vendor in a "clustered" dates 
    # desc_column_name = 'DescValue'
    # date_column_name = 'Transaction Date'
    # amount_column_name = 'Approved Amount (rpt)'
    # date_cluster_tolerance = '2 days'

    transaction_sorted = transactions.sort_values( [desc_column_name, date_column_name] )

    transaction_sorted['date_gap'] =  transaction_sorted[date_column_name]  - transaction_sorted.shift()[date_column_name]

    
    transaction_sorted['group_value'] = ( (transaction_sorted['date_gap'] < '0 days') | (transaction_sorted['date_gap'] > date_cluster_tolerance) ).cumsum()

    transaction_cluster = transaction_sorted.groupby([desc_column_name, 'group_value']).agg({ amount_column_name: ['sum', 'count'], date_column_name: ['min', 'max'] })

    return transaction_cluster

# def get_amex_group_missing_in_concur(amex_concur_left_join: pd.DataFrame) -> pd.DataFrame:

#     amexgrpmissing = amexgroupby[ (amex_concur_left_join['sum_concur'].isnull()) & (amex_concur_left_join['sum_amex'] > 0) ]

#     return amexgrpmissing

# def join_amex_grp_to_concur_by_sum_amount(amex_descgroup: pd.DataFrame, concur_descgroup: pd.DataFrame) -> pd.DataFrame:

#     # Find there are Concur DescValue group with same total amount as Amex groups that are missing completely in Concur
#     amexmissingmerge = amex_descgroup.reset_index().merge(
#         right = concur_descgroup.reset_index(), 
#         on = 'sum',
#         how = 'left',
#         suffixes= ('_amex', '_concur'),
#         indicator = True,
#         ).set_index('DescValue_amex')

#     descgroup_join_by_total_amount = amexmissingmerge[ amexmissingmerge['_merge'] == 'both' ]

#     return descgroup_join_by_total_amount