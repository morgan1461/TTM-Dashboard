# %%
import numpy as np
import pandas as pd
import glob
import os
from datetime import date

WORKDAY_REPORT_PATH = "K:/AP/TTM/Data/+ Data Repository/Dashboard/Staffing/Workday Reports/"

# --------------------------------
# Extraction functions
# -------------------------------

def load_workday_report(path=WORKDAY_REPORT_PATH):
    '''Loads the latest workday report from the dropoff directory

    Args:
        path (str): The path to the directory containing the Workday reports, default is WORKDAY_REPORT_PATH

    Returns:
        pd.DataFrame: The latest workday report as a pandas DataFrame
    '''
    latest_file = max(glob.glob(os.path.join(path, "*.xlsx")), key=os.path.getctime)
    return pd.read_excel(latest_file, header=1)

# -------------------------------
# Transformation functions
# -------------------------------

def clean_workday_report(df):
    '''Cleans the Workday report DataFrame into a more manageable format with necessary information

    Args:
        df (pd.DataFrame): The raw Workday report DataFrame

    Returns:
        pd.DataFrame: The cleaned Workday report DataFrame
    '''
    # separate out pertinent information
    cols = [
        'ID',                                   # jic
        'Legal Name in General Display Format', # full name
        'Legal Name - Last Name',
        'Legal Name - First Name',
        'Hire Date',                            # future trend use?
        'Job Family',                           # use to separate students from reg employees
        'Job Family Group',                     # same as above
        'Employee Type',                        # separate non students from ft and pt
        'FTE',                                  # jic for further use
        'Job Code',                             # to remove all student3 (sign shop and supervisors)
    ]
    # Job Family Group can be used to differentiate students from non student employees

    df_cut = df[cols]

    # rename columns for easier access
    df_cut.rename(columns={
        'Legal Name in General Display Format': 'full_name',
        'Legal Name - Last Name': 'last_name',
        'Legal Name - First Name': 'first_name',
        'Hire Date': 'hire_date',
        'Job Family': 'job_family',
        'Job Family Group': 'job_family_group',
        'Employee Type': 'employee_status',
        'FTE': 'fte',
        'Job Code': 'job_code'
    }, inplace=True)

    # drop non driver positions
    # NOTE: those with job_family_group == 'Unclassified'
    df_cut = df_cut[df_cut['job_family_group'] != 'Unclassified']
    # drop student3 positions
    df_cut = df_cut[df_cut['job_code'] != 'STUDENT3']

    # POTENTIALLY WANT TO SEPARATE STUDENT AND NON STUDENT EMPLOYEES INTO TWO DATAFRAMES FOR EASE OF USE IN DASHBOARD? 
    # (no having cdl status for full/part timers as they all must have cdl for the job)

    # confirm data types
    int_cols = ['ID']
    string_cols = ['full_name', 'last_name', 'first_name', 'job_family', 'job_family_group', 'employee_status', 'job_code']
    date_cols = ['hire_date']
    # enforce data types
    df_cut[int_cols] = df_cut[int_cols].astype('Int64')
    df_cut[string_cols] = df_cut[string_cols].astype('string').apply(lambda x: x.str.strip()) # ensure no whitespaces
    df_cut[date_cols] = df_cut[date_cols].astype('datetime64[us]')

    return df_cut

def transform_workday_report(df):
    '''
    Transforms the cleaned Workday report DataFrame into a format suitable for dashboard visualization

    Args:
        df (pd.DataFrame): The cleaned Workday report DataFrame

    Returns:
        pd.DataFrame: The transformed Workday report DataFrame
    '''
    # 


# %%
workday_report = load_workday_report()
# display(workday_report.head())

cleaned_workday_report = clean_workday_report(workday_report)

print(cleaned_workday_report.tail())
print(cleaned_workday_report.info())

# cleaned_workday_report.to_csv("K:/AP/TTM/Data/+ Data Repository/Dashboard/Staffing/cleaned_workday_report.csv", index=False)
# -------------------------------
# Load functions
# -------------------------------

# -------------------------------
# Master control
# -------------------------------

# if __name__ == "__main__":
#     # Load the latest Workday report
#     workday_df = load_workday_report()

#     print(workday_df)

# %%