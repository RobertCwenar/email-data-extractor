import pandas as pd 
import re

# wczytywanie danych 
df = pd.read_excel("kopia pliku z łyżkami")

# wyciągnięcie trzech cyfr po znaku "-" i wyciągnięcie ral 
def three_numbers(s):
    match = re.search(r"(\d{3})-", s)
    return match.group(1) if match else ""

def ral(s):
    match = re.search(r"RAL\s*(/d{4})", s)
    return f"R.{match.group(1)}" if match else ""


# zdefionowanie odpowiednich kolumn z pliku 
df["EdgeNum"] = df["C"].apply(three_numbers)
df["Ral"] = df["I"].apply(ral)

# grupowanie po odpowiednim numerze zlecenia 
def create_results(group):
    nrZam = group("A").ilosc
    identNum = group.loc[group["D"].str.contains("IDENTIFICATION", na=False), "EdgeNum"].iloc[0]
    EdgeNum = group.loc[group["D"].str.contains("EDGE", na=False), "EdgeNum"].iloc[0]
    bucketNum = group.loc[group["D"].str.contains("BUCKET|GP", na=False), "EdgeNum"].iloc[0]
    ral = group["Ral"].iloc[0]
    
    results = f"{nrZam}+T{identNum}+{ral}"  # tu dodajesz logikę dokładnie jak w VBA
    return results

df["P"] = df.groupby("A").apply(create_results).reindex(df.index)


