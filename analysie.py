import pandas as pd 
import re

# wczytywanie danych 
df = pd.read_excel("Example2.xlsx")

# wyciągnięcie trzech cyfr po znaku "-" i wyciągnięcie ral 
def three_numbers(s):
    match = re.search(r"(\d{3})-", s)
    return match.group(1) if match else ""

def ral(s):
    match = re.search(r"RAL\s*(/d{4})", s)
    return f"R.{match.group(1)}" if match else ""

df.columns = df.columns.str.strip()
print(df.columns)

# zdefionowanie odpowiednich kolumn z pliku 
df["EdgeNum"] = df["Nr materiału"].apply(three_numbers)
df["Ral"] = df["KOLOR RAL"].apply(ral)
df["nrZam"] = df["Nr zamówienia"].apply

# grupowanie po odpowiednim numerze zlecenia 
def create_results(group):
    mask_edge = group["Opis"].astype(str).str.contains("Edge", na=False)
    EdgeNum = group.loc[mask_edge, "Nr materiału"].iloc[0] if mask_edge.any() else ""

    mask_ident = group["Opis"].astype(str).str.contains("IDENT", na=False)
    IdentNum = group.loc[mask_ident, "Nr materiału"].iloc[0] if mask_ident.any() else ""

    mask_bucket = group["Opis"].astype(str).str.contains("BUCKET", na=False)
    BucketNum = group.loc[mask_bucket, "Nr materiału"].iloc[0] if mask_bucket.any() else ""

    mask_ral = group["Opis"].astype(str).str.contains("Special Painting", na=False)
    RalKod = group.loc[mask_ral, "KOLOR RAL"].iloc[0] if mask_ral.any() else ""
    
    results = f"{"Nr Zamówienia"}+T{IdentNum}+{ral}" 
    return results

df["P"] = df.groupby("Nr zamówienia").apply(create_results).reindex(df.index)


df = pd.to_excel("NewFile.xlsx", index = False)
print("Zapisano nowy plik!")