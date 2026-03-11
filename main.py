import pandas as pd
import docx as Document


def row_generator(df):
    yield df.columns.tolist()

    for index, row in df.iterrows():
        yield row.tolist()

def add_table_to_docx(df: pd.DataFrame, doc: Document) -> None:
    table = doc.add_table((len(df) + 1), len(df.columns))
    table.style = 'Table Grid'

    data_for_table = row_generator(df)

    for i, row in enumerate(data_for_table):
        for j, cell in enumerate(row):
            table.cell(i, j).text = str(cell)

if __name__ == "__main__":
    df = pd.read_excel("data/dataset.xlsx")
    df['Data urodzenia'] = df['Data urodzenia'].dt.strftime('%Y-%m-%d')
    df['Czy aktywny?'] = df['Czy aktywny?'].map({True: 'Tak', False: 'Nie'})

    doc = Document.Document()
    doc.add_heading("Siply document")
    add_table_to_docx(df, doc)
    doc.save("results/document.docx")