from io import BytesIO

import pandas as pd


def build_excel(metrado_df: pd.DataFrame, raw_rows: list[dict]) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        metrado_df.to_excel(writer, sheet_name="Metrado", index=False)
        pd.DataFrame(raw_rows).to_excel(writer, sheet_name="Mediciones base", index=False)

        for sheet in writer.book.worksheets:
            for column_cells in sheet.columns:
                max_length = max(len(str(cell.value or "")) for cell in column_cells)
                sheet.column_dimensions[column_cells[0].column_letter].width = min(max_length + 2, 45)

    output.seek(0)
    return output.read()
