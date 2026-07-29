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