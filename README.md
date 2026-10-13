# The Ohio State University Department of Transportation and Traffic Management Dashboard

A scalable administrative dashboard built within the python shiny-express framework. Each dashboard page has a backend module that operates independently while sharing the data to the dashboard through a centralized repository.

*Author:* Clay Morgan (Morgan.1461)

---

## Quick Links
| Module | Status | Description | Link |
| :--- | :--- | :--- | :--- | 
| **Dashboard** | `In Progress` | Web app front end dashboard | [Go to Dashboard Docs](#1-Dashboard-Module) |
| **Staffing** | `In Progress` | Backend staffing data extraction, cleaning, and loading | [Go to Staffing Docs](#1-Staffing-Module) |
| **Ridership** | `Planned` | Backend ridership data extraction, cleaning, and loading | [Go to Ridership Docs](#1-Ridership-Module) |


## Project Directory Map 

```
TTM-Dashboard/
│
├── 📁 dashboard/               # Front end 
│   ├── app.py                  # Shiny-express framework controller
│   ├── shared.py               # Module to trigger to pull each new data set
│   └── styles.css              # styling
│
├── 📁 database/                # Local SQLite backend (staffing_db.py)
│
├── 📁 staffing/                # Staffing data 
│   ├── staffing.py             # Pull data and save to central repository
│   └── requirements.txt  
│
├── requirements.txt
├── README.md
└── .gitignore
```

## Data Repository Map

All data for this dashboard will be saved on the K drive in a centralized repository at the following file path and structure:

```
K:/AP/TTM/Data/+ Data Repository/Dashboard/
|
├── 📁 Staffing/
|   ├── 📁 dashboard_data/      # Parent container for all cleaned data use in the staffing dashboard
|   |   ├── 📁 full_time/       
|   |   ├── 📁 part_time/   
|   |   └── 📁 student/
|   |
|   ├── 📁 Workday Reports/     # The drop point for raw workday current worker detail repots to be saved to for staffing dashboard
|   |   
|   ├── 📁 Training Staffing Master archive/ # An archive to save copies of the training and staffing master file if enabled in the code
|   |
|   └── 📁 TEMP Training Staffing Master/ # A temporary place to copy traning and staffing master files to until this is
|

```

### Staffing SQL database

Staffing data is stored in a local SQLite database (`data/ttm_dashboard.db`, override with the `TTM_DB_PATH` env var) in the table `staffing_snapshots`, keyed by `(snapshot_date, employee_type, employee_id)` so reloads never duplicate rows. `staffing.save_data` replaces the snapshot for a given date/type; the dashboard reads from the database. On first run with an empty database, `dashboard/shared.py` imports any legacy `full_time/`, `part_time/`, `student/` CSVs.

#### Biweekly employee update

`staffing/update_employees.py` takes the Workday Current Worker Detail report and the Termination report and updates the `employees` table (one row per employee ID: `employee_type`, `last_name`, `first_name`, `hire_date`, `termination_date` (empty if active), termination category/reason, job info, and optional CDL fields). Employee ID is the only key used to match records between the reports.

```
python staffing/update_employees.py <current_worker.xlsx> <terminations.xlsx> <report_date YYYY-MM-DD> [training_staffing_master.xlsx]
```

Runs are idempotent. Rehired employees (hire date after their termination date) get their termination cleared. The active roster is also recorded in `staffing_snapshots` for the report date, which feeds the dashboard trend charts.

---

### 1-Dashboard-Module

The dashboard module contains the user facing web interface built using Shiny for Python (Shiny Express). This provides real time interactive data visualizations and key performance indicators powered by data that is loadedinto the central dashboard data repository.

**Core Features**

- 

**Module Architecture**

| **File** | **Function** |
| :--- | :--- |
| `app.py` |  |
| `shared.py` |  |
| `styles.css` |  |

**Future Improvements and Known Issues**

- 

---

### 2-Staffing-Module

Back end data pull, clean, save to repo

`K:\AP\TTM\Data\+ Data Repository\Dashboard\Staffing\`

**Core Features**

- 

**Module Architecture**

| **File** | **Function** |
| :--- | :--- |
| `staffing.py` |  |
| `student_mapping.py` |  |

**Future Improvements and Known Issues**

- Training and Staffing Master file could be automatically pulled using a sharepoint API
    - Also add the full time and part time employees to the data pulled from the training staffing master for more robust future data use

---

### 3-Ridership-Module

Back end data for ridership
Busstate files?