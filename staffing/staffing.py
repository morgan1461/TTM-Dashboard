import numpy as np
import pandas as pd
import glob
import os
from datetime import date
from student_mapping import student_map, inactive_students

# Paths:
WORKDAY_REPORT_PATH = "K:/AP/TTM/Data/+ Data Repository/Dashboard/Staffing/Workday Reports/"
ARCHIVED_TRAINING_STAFFING_MASTER_PATH = "K:/AP/TTM/Data/+ Data Repository/Dashboard/Staffing/Training Staffing Master archive/"
STAFFING_DATA_REPOSITORY_PATH = 'K:/AP/TTM/Data/+ Data Repository/Dashboard/Staffing/dashboard_data/'

# temp for manual pulling as of now , delete after access is fixed and implemented
TEMP_TRAINING_STAFFING_MASTER_PATH = "K:/AP/TTM/Data/+ Data Repository/Dashboard/Staffing/TEMP Training Staffing Master"

# date variable for running historical data for now and abs path to file
file_name = "current_worker_detail_report_07_19_2026"
HIST_PATH = f"K:/AP/TTM/Data/+ Data Repository/Dashboard/Staffing/Workday Reports/{file_name}.xlsx"
DATE = pd.to_datetime("7/19/2026").date()

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

def load_workday_report_from_path(file_path):
    '''Loads a workday report from a specified file path

    Args:
        file_path (str): The full path to the Workday report file
    
    Returns:
        pd.DataFrame: The Workday report as a pandas DataFrame
    '''
    return pd.read_excel(file_path, header=1)

def load_training_staffing_master():
    '''
    this will be the automated pull function when I get access to implement
    '''
    return

def TEMP_load_training_staffing_master(path=TEMP_TRAINING_STAFFING_MASTER_PATH, archive_path=ARCHIVED_TRAINING_STAFFING_MASTER_PATH, archive=False):
    '''Temp function to pull the student cdl data from the training and staffing master file manually placed.
    Most recent file is taken from the folder, and an "archive" is saved in the path, this will be more relevant with the automated system, testing here

    UPDATE (8-6-2026): Employee ID has been added to the training and staffing master file so that this can be used to map together going forward.
    
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
        'ID': 'employee_id',
        'Legal Name in General Display Format': 'full_name_workday',
        'Legal Name - Last Name': 'last_name',
        'Legal Name - First Name': 'first_name',
        'Hire Date': 'hire_date_workday',
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
    int_cols = ['employee_id']
    string_cols = ['full_name_workday', 'last_name', 'first_name', 'job_family', 'job_family_group', 'employee_status', 'job_code']
    date_cols = ['hire_date_workday']
    # enforce data types
    df_cut[int_cols] = df_cut[int_cols].astype('Int64')
    df_cut[string_cols] = df_cut[string_cols].astype('string').apply(lambda x: x.str.strip()) # ensure no whitespaces
    df_cut[date_cols] = df_cut[date_cols].astype('datetime64[us]')

    return df_cut

def transform_workday_report(df, is_student=False, is_full_time=False, snapshot_date=DATE):
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

    df.rename(columns={'ID': 'id'})

    if is_student:
        df = df[(df['job_family_group'] == student_job_family_group) & (df['job_family'] == student_job_family)]
        df['cdl_status'] = None # will add in with other data pulled later
    
        #parse out irrelevant cols now and add student col
        df['employee_type'] = 'student'
        df['date'] = pd.to_datetime(snapshot_date)
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
            df['date'] = pd.to_datetime(snapshot_date)
            df.drop(columns=drop_cols, inplace=True)
            return df

        # part time
        elif not is_full_time:
            df = df[(df['employee_status'] == pt_employee_status) & (df['fte'] == pt_fte)]
            df['employee_type'] = 'part_time'
            df['date'] = pd.to_datetime(snapshot_date)
            df.drop(columns=drop_cols, inplace=True)
            return df

        # jic
        else:
            print("ERROR: No matching employee type found for the given data. Please check the input DataFrame.")
            return pd.DataFrame()  # return an empty DataFrame if no conditions are met

def clean_student_training_staffing_master(df):
    '''Clean up pertinent information from the student sheet of training and staffing master and remove unnecessary information

    UPDATE (8-6-2026): Employee ID has been added to the training and staffing master file so that this can be used to map together going forward.
    
    Args: 
        df (pd.DataFrame): The raw training and staffing excel sheet for students DataFrame
    Returns:
        pd.DataFrame: The cleaned student  DataFrame
    '''
    # goal: split into CDL, non-CDL, and training for CDL
    cols_to_keep = [
        'Name',
        'Employee ID',
        'Drivers #',
        'Active',
        'Permit',
        'CDL',
        'Hire Date',
        'Student CDL Training Start Date',
    ]

    df = df[cols_to_keep]

    df = df.rename(columns={
        'Name': 'full_name_tsm',
        'Employee ID': 'employee_id',
        'Drivers #': 'driver_num',
        'Active': 'active',
        'Permit': 'permit',
        'CDL': 'cdl',
        'Hire Date': 'hire_date_tsm',
        'Student CDL Training Start Date': 'cdl_training_start_date',
    })

    # remove all non active student employees
    df = df[df['active'] == 1]

    df['employee_id'] = df['employee_id'].astype('Int64')

    return df

# Potential problem here where will need to manually flag students in historic data
#
#

def merge_workday_training_staffing_student(workday_df, training_staffing_master_df, student_map=student_map, inactive_students=inactive_students):
    '''Merge the workday report with the student page of the training and staffing master report.
    NOTE: This is going to require a lot of specific rules to ensure that everyone is accounted for, if something breaks it will likely be here.
    NOTE: The student mapping dict will need manually updated for now each time a new student is added

    UPDATE (8-6-2026): Employee ID has been added to the training and staffing master file, this can be used to map together going forward.

    Args:
        workday df (pd.DataFrame): The cleaned workday report as pandas df
        training_staffing_master_df (pd.DataFrame): The cleaned student training master report as a pandas df
        student_mapping (dict): A map of the student employee names to match on each sheet, key: workday full_name, value: training_staffing master full_name
        inactive_students (list): A list of student employees that are no longer active, should be updated as we go
    Returns:
        pd.DataFrame: A raw merged dataframe with all currently counted student employees and their cdl status information
    '''
    # Map workday names to TSM names; keep original when no mapping exists.
    merged_workday_df = workday_df.copy()


    merged_df = merged_workday_df.merge(
        training_staffing_master_df,
        how='left',
        left_on='employee_id',
        right_on='employee_id'
    )

    return merged_df

def clean_merged_student_df(df):
    '''Takes the merged student report from both workday and traning excel sheet and cleans up for dashboard purposes.
    NOTE: Will need updated if we take the route of having some student be permanently non-cdl drivers
    
    Args:
        df (pd.DataFrame): The raw merged dataframe from workday and the training and staffing excel sheet
    Returns:
        pd.DataFrame: A cleaned version containing a concise cdl status col that will be ready for the dashboard
    '''
    # ensure datatypes are correct
    bool_cols = ['active', 'permit', 'cdl']
    datetime_col = 'cdl_training_start_date'

    df[bool_cols] = df[bool_cols].fillna(False).astype(int)
    df[datetime_col] = pd.to_datetime(df[datetime_col], errors='coerce')

    # impute cdl_status based on existing cols
    # define conditions
    conditions = [
        df['cdl'] == 1,
        (df['cdl'] == 0) & (df['cdl_training_start_date'].isna()),
        (df['cdl'] == 0) & (df['cdl_training_start_date'].notna())
    ]

    response = [
        'cdl',
        'non-cdl',
        'training-cdl'
    ]

    df['cdl_status'] = np.select(conditions, response, default='unknown')

    # clean up bloat
    cols_to_drop = ['mapped_full_name', 'full_name_tsm', 'hire_date_tsm']
    df = df.drop(columns=cols_to_drop)

    # rename and reorder cols?
    df.rename(columns={
        'full_name_workday': 'full_name',
        'hire_date_workday': 'hire_date',
    }, inplace=True)

    # final: add current date to col for date data was pulled?
    df['date'] = pd.to_datetime(DATE)

    return df

# -------------------------------
# Load functions
# -------------------------------

def save_data(df, is_full_time=False, is_part_time=False, is_student=False, data_repo_path=STAFFING_DATA_REPOSITORY_PATH, date=date.today()):
    '''Save the data to the central repository containing the staffing data for the dashboard
    
    Args:
        df (pd.DataFrame): The final cleaned and saved df
        is_full_time (boolean): Save to full time
        is_part_time (boolean): Save to part time
        is_student (boolean): Save to student
        data_repo_path (string): The path to the central repository containing staffing data for the dashboard
        date (datetime.date): The date the data is pulled, default is today
    Returns:
        None
    '''
    # NOTE: Add conditional checking to ensure not "{double booked"
    if is_full_time:
        df.to_csv(f'{data_repo_path}full_time/{str(date)}_full_time.csv', index=False)
    elif is_part_time:
        df.to_csv(f'{data_repo_path}part_time/{str(date)}_part_time.csv', index=False)
    elif is_student:
        df.to_csv(f'{data_repo_path}student/{str(date)}_student.csv', index=False)
    else:
        print('Failure: ensure that at least one bool expression is checked.')

    return None

# -------------------------------
# Student Staffing Trends functions
# -------------------------------
'''

'''

# -------------------------------
# Master control
# -------------------------------

if __name__ == "__main__":

    # STEP 1: Extract raw data from the 2 sources
    workday_report = load_workday_report_from_path('K:\\AP\\TTM\\Data\\+ Data Repository\\Dashboard\\Staffing\\Workday Reports\\Current_Worker_Detail_Report_07_19_2026.xlsx') # testing purposes
    training_staffing_master_report = TEMP_load_training_staffing_master(archive=False) # EDIT ONCE THIS IS AUTOMATED
    print("Data extraction complete.")

    # STEP 2: Transform and clean the raw data
    cleaned_workday_report = clean_workday_report(workday_report)
    print("Workday report cleaned.")

    # extract ft, pt, students
    full_time_df = transform_workday_report(cleaned_workday_report, is_full_time=True)
    print("Full-time report transformed.")
    part_time_df = transform_workday_report(cleaned_workday_report)
    print("Part-time report transformed.")
    workday_student_df = transform_workday_report(cleaned_workday_report, is_student=True)
    print("Workday student report transformed.")

    # traning staffing master for additional student cols
    cleaned_training_staffing_master_report = clean_student_training_staffing_master(training_staffing_master_report)
    print("Training staffing master report cleaned.")

    # print(workday_student_df.head())
    # print(workday_student_df.info())
    # print(cleaned_training_staffing_master_report.head())
    # print(cleaned_training_staffing_master_report.info())

    # merge these 2 dfs for students
    merged_student_df = merge_workday_training_staffing_student(workday_student_df, cleaned_training_staffing_master_report)
    print("Merged student report")
    print(merged_student_df.head())
    print(merged_student_df.shape)
    merged_student_df.to_csv('merge_test.csv', index=False)

    cleaned_training_staffing_master_report.to_csv('cleaned_training_staffing_master_report.csv', index=False)
    cleaned_workday_report.to_csv('cleaned_workday_report.csv', index=False)

    # cleaned_merged_student_df = clean_merged_student_df(merged_student_df)
    # print("Cleaned merged student report")
    # print(cleaned_merged_student_df.head())
    # print(cleaned_merged_student_df.shape)

    # STEP 3: Load the data to the centralized repo
    # save_data(full_time_df, is_full_time=True, date=DATE)
    # save_data(part_time_df, is_part_time=True, date=DATE)
    # save_data(cleaned_merged_student_df, is_student=True, date=DATE)
    # print("Data saved to central repository with date: " + str(DATE))

    # training_staffing_master_report.to_csv(f'tsm_trending_list.csv', index=False)