import pandas as pd
p = r"c:\Users\jferr\OneDrive\Desktop\HR_Reconcile\PHR CAO 07JUL.XLSX"
df = pd.read_excel(p)
for col in ['LIN Number / DODIC','Serial Number','Serial no. profile','Batch']:
    if col in df.columns:
        vals = df[col].dropna().astype(str)
        sample = vals[vals.str.strip().str.len()>0].head(50).tolist()
        print(f"\nColumn: {col} (samples {len(sample)})")
        for v in sample:
            print(' ', v)
    else:
        print(f"\nColumn: {col} not found")
