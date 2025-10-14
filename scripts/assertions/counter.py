from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from .base import BaseAssertionPlugin
from .registry import register


@register
class CounterPlugin(BaseAssertionPlugin):
    plugin_name = "counter"
    sheet_name = "Counter"

    def parse(self, xls_path: Path) -> Dict[str, Any]:
        # Find sheet case-insensitively
        import openpyxl
        wb = openpyxl.load_workbook(xls_path, read_only=True, data_only=True)
        actual_sheet_name = self.find_sheet_case_insensitive(wb.sheetnames, self.sheet_name)
        wb.close()
        
        if not actual_sheet_name:
            raise ValueError(f"Sheet '{self.sheet_name}' not found in Excel. Available sheets: {wb.sheetnames}")
        
        raw = pd.read_excel(xls_path, sheet_name=actual_sheet_name, header=None)
        cnt_left_header = raw.iloc[0, 0]
        cnt_right_header = raw.iloc[0, 5]

        # Left table: first 5 columns
        left_header = raw.iloc[1, 0:5].tolist()
        left = raw.iloc[2:, 0:5].copy()
        left.columns = left_header
        left = self._keep_non_empty_rows(left)

        # Right table: next 4 columns
        right_header = raw.iloc[1, 5:9].tolist()
        right = raw.iloc[2:, 5:9].copy()
        right.columns = right_header
        right = self._keep_non_empty_rows(right)

        return {
            "cnt_left_header": cnt_left_header,
            "cnt_right_header": cnt_right_header,
            "left_header": left_header,
            "right_header": right_header,
            cnt_left_header: left.to_dict(orient="records"),
            cnt_right_header: right.to_dict(orient="records"),
        }

    def generate_sv(self, parsed: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
        CG = parsed
        cg1 = CG.get(CG.get("cnt_left_header")) or []
        cg2 = CG.get(CG.get("cnt_right_header")) or []
        cg1_header_name = CG.get("left_header") or []
        cg2_header_name = CG.get("right_header") or []

        from collections import defaultdict, OrderedDict

        cnt_base = OrderedDict()
        for row in cg1:
            cname = (row.get(cg1_header_name[0]) or "")
            if cname and cname not in cnt_base:
                cnt_base[cname] = row
        cnt_conds = defaultdict(list)
        for row in cg2:
            cname = (row.get(cg2_header_name[0]) or "")
            if cname:
                cnt_conds[cname].append(row)
        cnt_sections = []
        for name, base in cnt_base.items():
            clk_edge = (base.get(cg1_header_name[1]) or "")
            clk = (base.get(cg1_header_name[2]) or "")
            rst_edge = (base.get(cg1_header_name[3]) or "")
            rst = (base.get(cg1_header_name[4]) or "")
            has_reset = bool(rst_edge and rst)
            sens = f"{clk_edge} {clk}" if not has_reset else f"{clk_edge} {clk} or {rst_edge} {rst}"

            cnt_lines = [f"always @({sens}) begin"]
            conds = cnt_conds.get(name, [])
            for i, c in enumerate(conds):
                st = (c.get(cg2_header_name[1]) or "").lower()
                cond = (c.get(cg2_header_name[2]) or "")
                cons = (c.get(cg2_header_name[3]) or "")
                if i == 0 or st == "if":
                    cond_expr = cond if cond else "1'b0"
                    cnt_lines.append(f"    if ({cond_expr}) begin")
                    if cons:
                        cnt_lines.append(f"        {cons};")
                    cnt_lines.append("    end")
                elif st == "else if":
                    cond_expr = cond if cond else "1'b0"
                    cnt_lines.append(f"    else if ({cond_expr}) begin")
                    if cons:
                        cnt_lines.append(f"        {cons};")
                    cnt_lines.append("    end")
                else:
                    cnt_lines.append("    else begin")
                    if cons:
                        cnt_lines.append(f"        {cons};")
                    cnt_lines.append("    end")
            cnt_lines.append("end")
            cnt_sections.append(f"// ---- {name} ----\n" + "\n".join(cnt_lines))

        return cnt_sections

    @staticmethod
    def _keep_non_empty_rows(df):
        df = df.fillna("").infer_objects(copy=False)
        keep = []
        for i in range(len(df)):
            row = df.iloc[i]
            has_value = False
            for value in row:
                if str(value).strip() != "":
                    has_value = True
                    break
            keep.append(has_value)
        df = df.loc[keep].reset_index(drop=True)
        for col in df.columns:
            df[col] = df[col].apply(lambda x: str(x).strip() if isinstance(x, str) else x)
        return df


