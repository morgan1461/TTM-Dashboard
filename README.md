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

## Data Repository

All data for this dashboard will be saved on the K drive in a centralized repository at the following file path:

`K:\AP\TTM\Data\+ Data Repository\Dashboard\`

---

### 1-Dashboard-Module

Front end

---

### 2-Staffing-Module

Back end data pull, clean, save to repo

`K:\AP\TTM\Data\+ Data Repository\Dashboard\Staffing\`

---

### 3-Ridership-Module

Back end data for ridership
Busstate files?