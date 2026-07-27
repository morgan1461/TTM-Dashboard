import numpy as np
import pandas as pd
import glob
import os
from datetime import date
from student_mapping import student_map

# Paths:
WORKDAY_REPORT_PATH = "K:/AP/TTM/Data/+ Data Repository/Dashboard/Staffing/Workday Reports/"
ARCHIVED_TRAINING_STAFFING_MASTER_PATH = "K:/AP/TTM/Data/+ Data Repository/Dashboard/Staffing/Training Staffing Master archive/"

# temp for manual pulling as of now , delete after access is fixed and implemented
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

def TEMP_load_training_staffing_master(path=TEMP_TRAINING_STAFFING_MASTER_PATH, archive_path=ARCHIVED_TRAINING_STAFFING_MASTER_PATH, archive=False):
    '''Temp function to pull the student cdl data from the training and staffing master file manually placed.
    Most recent file is taken from the folder, and an "archive" is saved in the path, this will be more relevant with the automated system, testing here
    
    Args: 
        path (str): The path to the directory containing a manually copied report
        archive_path (str): The path to archive a copy of the training staffing master, in case of need to audit in future.
        archive (bool): Determines if should be archived in the archive path or not, default False
    Returns:
        pd.DataFrame: 
    '''
    latest_file = max(glob.glob(os.path.join(path, "*.xlsx")), key=os.path.getctime)
    student_data = pd.read_excel(latest_file, sheet_name='Students')

    # save to excel
    if archive:
        student_data.to_excel(archive_path + f"{str(date.today())}_archived.xlsx")

    return student_data

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

def clean_student_training_staffing_master(df):
    '''Clean up pertinent information from the student sheet of training and staffing master and remove unnecessary information
    
    Args: 
        df (pd.DataFrame): The raw training and staffing excel sheet for students DataFrame
    Returns:
        pd.DataFrame: The cleaned student  DataFrame
    '''
    # goal: split into CDL, non-CDL, and training for CDL
    cols_to_keep = [
        'Name',
        'Drivers #',
        'Active',
        'Permit',
        'CDL',
        'Hire Date',
        'Student CDL Training Start Date'
    ]

    df = df[cols_to_keep]

    df = df.rename(columns={
        'Name': 'full_name', # hopefully will match up decently well with other df
        'Drivers #': 'driver_num',
        'Active': 'active',
        'Permit': 'permit',
        'CDL': 'cdl',
        'Hire Date': 'hire_date',
        'Student CDL Training Start Date': 'cdl_training_start_date',
    })

    # remove all non active student employees
    df = df[df['active'] == 1]

    return df

def merge_workday_training_staffing_student(workday_df, training_staffing_master_df, student_map=student_map):
    '''Merge the workday report with the student page of the training and staffing master report.
    NOTE: This is going to require a lot of specific rules to ensure that everyone is accounted for, if something breaks it will likely be here.
    NOTE: The student mapping dict will need manually updated for now each time a new student is added

    Args:
        workday df (pd.DataFrame): The cleaned workday report as pandas df
        training_staffing_master_df (pd.DataFrame): The cleaned student training master report as a pandas df
        student_mapping (dict): A map of the student employee names to match on each sheet, key: workday full_name, value: training_staffing master full_name
    Returns:
        pd.DataFrame: A raw merged dataframe with all currently counted student employees and their cdl status information
    '''


    return

def clean_merged_student_df(df):
    '''Takes the merged student report from both workday and traning excel sheet and cleans up for dashboard purposes.
    
    Args:
        df (pd.DataFrame): The raw merged dataframe from workday and the training and staffing excel sheet
    Returns:
        pd.DataFrame: A cleaned version containing a concise cdl status col that will be ready for the dashboard
    '''
    return

# -------------------------------
# Load functions
# -------------------------------

# -------------------------------
# Master control
# -------------------------------
workday_report = load_workday_report()
# # display(workday_report.head())

cleaned_workday_report = clean_workday_report(workday_report)

student_df = transform_workday_report(cleaned_workday_report, is_student=True)
# full_time_df = transform_workday_report(cleaned_workday_report, is_student=False, is_full_time=True)
# part_time_df = transform_workday_report(cleaned_workday_report, is_student=False, is_full_time=False)

# print(f"Student Employees: {student_df.shape[0]}")
# print(student_df.head())

# print(f"Full Time Employees: {full_time_df.shape[0]}")
# print(full_time_df.head())
# print(f"Part Time Employees: {part_time_df.shape[0]}")
# print(part_time_df.head())
df = TEMP_load_training_staffing_master(archive=False)
tsm_student_df = clean_student_training_staffing_master(df)
# print(tsm_student_df.head())
# print(tsm_student_df.shape)
print(student_map)
print(type(student_map))
print(len(student_map))


# if __name__ == "__main__":
#     # Load the latest Workday report
#     workday_df = load_workday_report()

#     print(workday_df)


