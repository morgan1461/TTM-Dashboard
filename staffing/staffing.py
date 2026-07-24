# %%
import numpy as np
import pandas as pd
import glob
import os
from datetime import date

WORKDAY_REPORT_PATH = "K:/AP/TTM/Data/+ Data Repository/Dashboard/Staffing/Workday Reports/"
# temp for manual pulling as of now
TEMP_TRAINING_STAFFING_MASTER_PATH = "K:/AP/TTM/Data/+ Data Repository/Dashboard/Staffing/TEMP Training Staffing Master"
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

def load_training_staffing_master():
    '''
    this will be the automated pull function when I get access to implement
    '''
    return

def TEMP_load_training_staffing_master(path):
    '''
    
    Args: 
        path (str): The path to the directory containing a manually copied report
    '''

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

def transform_workday_report(df, is_student=False, is_full_time=False):
    '''
    Transforms the cleaned Workday report DataFrame into a format suitable for dashboard visualization
    FUTURE: Add logs to determine if a student 3 slips through or theres any missing data???
    Args:
        df (pd.DataFrame): The cleaned Workday report DataFrame
        is_student (bool): Flag indicating whether to filter for student employees, adds an empty CDL col, default is False

    Returns:
        pd.DataFrame: The transformed Workday report DataFrame in the format for the dashboard
    '''
    # Cols:
    # id | full_name | last_name | first_name | hire_date | employee_type | cdl
    # NOTE: Maybe split the 3 types into 3 separate dataframes?????
    student_job_family = "Student Employee - Hourly"
    student_job_family_group = "Students"

    drop_cols = ['job_family', 'job_family_group', 'employee_status', 'fte', 'job_code']

    if is_student:
        df = df[(df['job_family_group'] == student_job_family_group) & (df['job_family'] == student_job_family)]
        df['cdl_status'] = None # will add in with other data pulled later
    
        #parse out irrelevant cols now and add student col
        df['employee_type'] = 'student'
        df.drop(columns=drop_cols, inplace=True)
        return df

    # have to split full timers and part timers now
    else: # either ft or pt
        ft_employee_status = "Regular"
        ft_fte = 1

        pt_employee_status = "Intermittent"
        pt_fte = 0.005

        # fulltimers
        if is_full_time:
            df = df[(df['employee_status'] == ft_employee_status) & (df['fte'] == ft_fte)]
            df['employee_type'] = 'full_time'
            df.drop(columns=drop_cols, inplace=True)
            return df

        # part time
        elif not is_full_time:
            df = df[(df['employee_status'] == pt_employee_status) & (df['fte'] == pt_fte)]
            df['employee_type'] = 'part_time'
            df.drop(columns=drop_cols, inplace=True)
            return df

        # jic
        else:
            print("ERROR: No matching employee type found for the given data. Please check the input DataFrame.")
            return pd.DataFrame()  # return an empty DataFrame if no conditions are met

# -------------------------------
# Load functions
# -------------------------------

# -------------------------------
# Master control
# -------------------------------
workday_report = load_workday_report()
# display(workday_report.head())

cleaned_workday_report = clean_workday_report(workday_report)

student_df = transform_workday_report(cleaned_workday_report, is_student=True)
full_time_df = transform_workday_report(cleaned_workday_report, is_student=False, is_full_time=True)
part_time_df = transform_workday_report(cleaned_workday_report, is_student=False, is_full_time=False)

print(f"Student Employees: {student_df.shape[0]}")
print(student_df.head())
print(f"Full Time Employees: {full_time_df.shape[0]}")
print(full_time_df.head())
print(f"Part Time Employees: {part_time_df.shape[0]}")
print(part_time_df.head())
# if __name__ == "__main__":
#     # Load the latest Workday report
#     workday_df = load_workday_report()

#     print(workday_df)

# %%