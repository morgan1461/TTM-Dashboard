from pathlib import Path

import pandas as pd

app_dir = Path(__file__).parent.parent
df = pd.read_csv(app_dir / "test_data.csv")
