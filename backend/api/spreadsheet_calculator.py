#!/usr/bin/env python3
"""
Generic spreadsheet calculator for processing natural language queries
against Excel spreadsheets with formulas.

Supports any well-structured spreadsheet with headers and formulas.
"""

import re
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import openpyxl
from openpyxl.utils import get_column_letter, column_index_from_string
import pandas as pd


class SpreadsheetCalculator:
    """
    Generic calculator for spreadsheet-based queries.

    Loads Excel files and processes natural language questions by:
    1. Detecting what data is being requested
    2. Finding relevant cells/sheets
    3. Evaluating formulas or returning values
    4. Formatting responses
    """

    def __init__(self, spreadsheet_path: str = None):
        """
        Initialize calculator with a spreadsheet.

        Args:
            spreadsheet_path: Path to Excel file (.xlsx)
        """
        self.spreadsheet_path = spreadsheet_path
        self.workbook = None
        self.workbook_data = None  # Pandas DataFrames with evaluated formulas
        self.sheet_index = {}  # Maps sheet names to content indices

        if spreadsheet_path:
            self.load_spreadsheet(spreadsheet_path)

    def load_spreadsheet(self, path: str):
        """
        Load an Excel spreadsheet and index its contents.

        Args:
            path: Path to .xlsx file
        """
        path_obj = Path(path)

        if not path_obj.exists():
            raise FileNotFoundError(f"Spreadsheet not found: {path}")

        if path_obj.suffix.lower() != '.xlsx':
            raise ValueError("Only .xlsx files are supported")

        self.spreadsheet_path = str(path_obj)
        self.workbook = openpyxl.load_workbook(path, data_only=False)

        # Load with pandas for formula evaluation
        self.workbook_data = pd.read_excel(path, sheet_name=None, engine='openpyxl')

        # Index all sheets
        self._index_sheets()

    def _index_sheets(self):
        """
        Create searchable index of all sheet contents.

        Indexes:
        - Sheet names
        - Headers (first row)
        - Categories/labels (first column)
        - All cell values and formulas
        """
        self.sheet_index = {}

        for sheet_name in self.workbook.sheetnames:
            sheet = self.workbook[sheet_name]

            # Extract headers (first row)
            headers = {}
            for col_idx, cell in enumerate(sheet[1], start=1):
                if cell.value:
                    col_letter = get_column_letter(col_idx)
                    headers[col_letter] = str(cell.value).lower()

            # Extract categories/labels (first column)
            categories = {}
            for row_idx, row in enumerate(sheet.iter_rows(min_row=1, max_col=1), start=1):
                cell = row[0]
                if cell.value:
                    categories[row_idx] = str(cell.value).lower()

            # Store complete cell map
            cell_map = {}
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.value is not None:
                        coord = cell.coordinate
                        cell_map[coord] = {
                            'value': cell.value,
                            'formula': cell.value if isinstance(cell.value, str) and cell.value.startswith('=') else None,
                            'data_type': cell.data_type,
                            'number_format': cell.number_format
                        }

            self.sheet_index[sheet_name.lower()] = {
                'name': sheet_name,
                'headers': headers,
                'categories': categories,
                'cells': cell_map,
                'max_row': sheet.max_row,
                'max_column': sheet.max_column
            }

    def detect_sheet(self, question: str) -> Optional[str]:
        """
        Detect which sheet the question is about.

        Args:
            question: User's natural language question

        Returns:
            Sheet name or None
        """
        question_lower = question.lower()

        # Check for explicit sheet mentions
        for sheet_key, sheet_info in self.sheet_index.items():
            sheet_name = sheet_info['name']
            if sheet_name.lower() in question_lower:
                return sheet_name

        # Check for keywords that match sheet purposes
        # Income-related keywords
        if any(kw in question_lower for kw in ['income', 'salary', 'revenue', 'earn']):
            for sheet_key in self.sheet_index:
                if 'income' in sheet_key:
                    return self.sheet_index[sheet_key]['name']

        # Expense-related keywords
        if any(kw in question_lower for kw in ['expense', 'spend', 'spent', 'cost', 'budget', 'actual']):
            for sheet_key in self.sheet_index:
                if 'expense' in sheet_key:
                    return self.sheet_index[sheet_key]['name']

        # Summary-related keywords
        if any(kw in question_lower for kw in ['summary', 'total', 'net', 'overall', 'savings rate', 'performance']):
            for sheet_key in self.sheet_index:
                if 'summary' in sheet_key or 'dashboard' in sheet_key:
                    return self.sheet_index[sheet_key]['name']

        # Default to first sheet or summary if available
        if 'summary' in self.sheet_index:
            return self.sheet_index['summary']['name']

        return list(self.sheet_index.values())[0]['name'] if self.sheet_index else None

    def find_category_row(self, sheet_name: str, category: str) -> Optional[int]:
        """
        Find the row number for a category/label.

        Args:
            sheet_name: Name of sheet
            category: Category to search for

        Returns:
            Row number or None
        """
        sheet_key = sheet_name.lower()
        if sheet_key not in self.sheet_index:
            return None

        category_lower = category.lower()
        categories = self.sheet_index[sheet_key]['categories']

        # Exact match
        for row_num, cat_text in categories.items():
            if category_lower == cat_text:
                return row_num

        # Partial match (category contains search term or vice versa)
        for row_num, cat_text in categories.items():
            if category_lower in cat_text or cat_text in category_lower:
                return row_num

        return None

    def find_column_by_header(self, sheet_name: str, header_keyword: str) -> Optional[str]:
        """
        Find column letter by header keyword.

        Args:
            sheet_name: Name of sheet
            header_keyword: Keyword to search for in headers

        Returns:
            Column letter or None
        """
        sheet_key = sheet_name.lower()
        if sheet_key not in self.sheet_index:
            return None

        keyword_lower = header_keyword.lower()
        headers = self.sheet_index[sheet_key]['headers']

        # Exact match
        for col_letter, header_text in headers.items():
            if keyword_lower == header_text:
                return col_letter

        # Partial match
        for col_letter, header_text in headers.items():
            if keyword_lower in header_text or header_text in keyword_lower:
                return col_letter

        return None

    def _evaluate_formula(self, sheet_name: str, formula: str) -> Any:
        """
        Evaluate simple Excel formulas.

        Args:
            sheet_name: Current sheet name for relative references
            formula: Formula string (e.g., '=SUM(B2:B6)')

        Returns:
            Evaluated result
        """
        formula = formula.strip()
        if not formula.startswith('='):
            return formula

        formula_content = formula[1:]  # Remove =

        # Handle cross-sheet references (e.g., Income!B7)
        if '!' in formula_content:
            parts = formula_content.split('!')
            if len(parts) == 2:
                ref_sheet = parts[0].strip()
                ref_cell = parts[1].strip()
                return self.get_cell_value(ref_sheet, ref_cell, evaluated=True)

        # Handle SUM function
        if formula_content.upper().startswith('SUM('):
            # Extract range (e.g., 'B2:B6')
            range_match = re.search(r'SUM\(([A-Z]+\d+):([A-Z]+\d+)\)', formula_content, re.IGNORECASE)
            if range_match:
                start_cell = range_match.group(1)
                end_cell = range_match.group(2)

                # Extract column and rows
                start_col = ''.join(filter(str.isalpha, start_cell))
                start_row = int(''.join(filter(str.isdigit, start_cell)))
                end_row = int(''.join(filter(str.isdigit, end_cell)))

                # Sum the range
                total = 0
                for row_num in range(start_row, end_row + 1):
                    cell_val = self.get_cell_value(sheet_name, f"{start_col}{row_num}", evaluated=True)
                    if isinstance(cell_val, (int, float)):
                        total += cell_val

                return total

        # Handle IF function: IF(condition, value_if_true, value_if_false)
        if formula_content.upper().startswith('IF('):
            # Parse IF with proper parenthesis matching
            # Find matching parentheses
            paren_count = 0
            start_idx = formula_content.upper().find('IF(') + 3
            comma_positions = []

            for i, char in enumerate(formula_content[start_idx:], start=start_idx):
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    if paren_count == 0:
                        # This is the closing paren for IF
                        end_idx = i
                        break
                    paren_count -= 1
                elif char == ',' and paren_count == 0:
                    comma_positions.append(i)

            if len(comma_positions) >= 2:
                condition_str = formula_content[start_idx:comma_positions[0]].strip()
                value_if_true_str = formula_content[comma_positions[0]+1:comma_positions[1]].strip()
                value_if_false_str = formula_content[comma_positions[1]+1:end_idx].strip()

                # Evaluate condition (e.g., 'B3=0')
                # Handle equality
                if '=' in condition_str and not any(op in condition_str for op in ['<=', '>=', '!=']):
                    parts = condition_str.split('=')
                    if len(parts) == 2:
                        left = self._eval_expression(sheet_name, parts[0].strip())
                        right = self._eval_expression(sheet_name, parts[1].strip())
                        condition_result = (left == right)

                        if condition_result:
                            return self._eval_expression(sheet_name, value_if_true_str)
                        else:
                            return self._eval_expression(sheet_name, value_if_false_str)

        # Handle arithmetic operations (e.g., 'B3-B7', 'B3-B6')
        for op in ['-', '+', '*', '/']:
            if op in formula_content:
                parts = formula_content.split(op)
                if len(parts) == 2:
                    left = self._eval_expression(sheet_name, parts[0].strip())
                    right = self._eval_expression(sheet_name, parts[1].strip())

                    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                        if op == '-':
                            return left - right
                        elif op == '+':
                            return left + right
                        elif op == '*':
                            return left * right
                        elif op == '/':
                            return left / right if right != 0 else 0

        return None

    def _eval_expression(self, sheet_name: str, expr: str) -> Any:
        """
        Evaluate an expression (cell reference, literal value, or arithmetic).

        Args:
            sheet_name: Current sheet name
            expr: Expression (e.g., 'B3', '100', '0', '(B3-B7)/B3')

        Returns:
            Evaluated value
        """
        expr = expr.strip()

        # Check if it's a number
        try:
            return float(expr)
        except ValueError:
            pass

        # Handle parenthesized expressions: (expr)
        if expr.startswith('(') and expr.endswith(')'):
            return self._eval_expression(sheet_name, expr[1:-1])

        # Check if it's a cell reference
        if re.match(r'^[A-Z]+\d+$', expr):
            return self.get_cell_value(sheet_name, expr, evaluated=True)

        # Check for cross-sheet reference
        if '!' in expr:
            parts = expr.split('!')
            if len(parts) == 2:
                ref_sheet = parts[0].strip()
                ref_cell = parts[1].strip()
                return self.get_cell_value(ref_sheet, ref_cell, evaluated=True)

        # Check if it's a formula
        if expr.startswith('='):
            return self._evaluate_formula(sheet_name, expr)

        # Handle arithmetic operations with proper precedence
        # First handle division and multiplication (left to right)
        for op in ['/', '*']:
            # Find rightmost operator not in parentheses
            paren_depth = 0
            for i in range(len(expr) - 1, -1, -1):
                if expr[i] == ')':
                    paren_depth += 1
                elif expr[i] == '(':
                    paren_depth -= 1
                elif expr[i] == op and paren_depth == 0:
                    left = self._eval_expression(sheet_name, expr[:i])
                    right = self._eval_expression(sheet_name, expr[i+1:])
                    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                        if op == '/':
                            return left / right if right != 0 else 0
                        elif op == '*':
                            return left * right

        # Then handle addition and subtraction (left to right)
        for op in ['+', '-']:
            # Find rightmost operator not in parentheses
            paren_depth = 0
            for i in range(len(expr) - 1, -1, -1):
                if expr[i] == ')':
                    paren_depth += 1
                elif expr[i] == '(':
                    paren_depth -= 1
                elif expr[i] == op and paren_depth == 0 and i > 0:  # i > 0 to avoid leading minus
                    left = self._eval_expression(sheet_name, expr[:i])
                    right = self._eval_expression(sheet_name, expr[i+1:])
                    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                        if op == '+':
                            return left + right
                        elif op == '-':
                            return left - right

        return expr

    def get_cell_value(self, sheet_name: str, cell_coord: str, evaluated: bool = True) -> Any:
        """
        Get value from a cell.

        Args:
            sheet_name: Name of sheet
            cell_coord: Cell coordinate (e.g., 'B3')
            evaluated: If True, evaluate formulas; if False, return formula text

        Returns:
            Cell value
        """
        sheet = self.workbook[sheet_name]
        cell = sheet[cell_coord]

        if not evaluated:
            return cell.value

        # If it's a formula, evaluate it
        if cell.value and isinstance(cell.value, str) and cell.value.startswith('='):
            return self._evaluate_formula(sheet_name, cell.value)

        return cell.value

    def extract_keywords(self, question: str) -> List[str]:
        """
        Extract potential category/field keywords from question.

        Args:
            question: User's question

        Returns:
            List of keywords
        """
        question_lower = question.lower()

        # Remove common question words
        stop_words = {
            'what', 'is', 'my', 'the', 'how', 'much', 'did', 'i', 'am', 'are',
            'was', 'were', 'do', 'does', 'can', 'could', 'should', 'would',
            'for', 'on', 'in', 'at', 'to', 'from', 'by', 'with', 'and', 'or'
        }

        # Split into words
        words = re.findall(r'\b\w+\b', question_lower)

        # Filter stop words and short words
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        return keywords

    def detect_query_type(self, question: str) -> str:
        """
        Detect what type of query this is.

        Returns:
            Query type: 'category_lookup', 'total', 'comparison', 'calculation', 'summary'
        """
        question_lower = question.lower()

        # Total/sum queries
        if any(kw in question_lower for kw in ['total', 'sum', 'all', 'combined']):
            return 'total'

        # Comparison queries
        if any(kw in question_lower for kw in ['over budget', 'under budget', 'difference', 'vs', 'versus', 'compared']):
            return 'comparison'

        # Calculation/metric queries
        if any(kw in question_lower for kw in ['rate', 'ratio', 'percentage', '%', 'percent']):
            return 'calculation'

        # Summary queries
        if any(kw in question_lower for kw in ['summary', 'overview', 'dashboard', 'net income', 'performance']):
            return 'summary'

        # Category lookup (specific item)
        return 'category_lookup'

    def process_category_lookup(self, question: str) -> Optional[Dict[str, Any]]:
        """
        Process a query asking about a specific category.

        E.g., "How much did I spend on groceries?"

        Args:
            question: User's question

        Returns:
            Result dictionary or None
        """
        # Detect sheet
        sheet_name = self.detect_sheet(question)
        if not sheet_name:
            return None

        # Extract keywords
        keywords = self.extract_keywords(question)

        # Try to find category
        category_row = None
        matched_category = None

        for keyword in keywords:
            row = self.find_category_row(sheet_name, keyword)
            if row:
                category_row = row
                matched_category = keyword
                break

        if not category_row:
            return None

        # Determine which column to read
        question_lower = question.lower()

        # Default column logic
        column = None
        column_desc = None

        if 'budgeted' in question_lower or 'budget' in question_lower:
            column = self.find_column_by_header(sheet_name, 'budgeted')
            column_desc = 'Budgeted'
        elif 'actual' in question_lower or 'spent' in question_lower:
            column = self.find_column_by_header(sheet_name, 'actual')
            column_desc = 'Actual'
        elif 'difference' in question_lower:
            column = self.find_column_by_header(sheet_name, 'difference')
            column_desc = 'Difference'
        elif 'monthly' in question_lower:
            column = self.find_column_by_header(sheet_name, 'monthly')
            column_desc = 'Monthly'
        elif 'annual' in question_lower or 'year' in question_lower:
            column = self.find_column_by_header(sheet_name, 'annual')
            column_desc = 'Annual'
        else:
            # Default to second column (usually the main value column)
            column = 'B'
            column_desc = 'Amount'

        if not column:
            column = 'B'
            column_desc = 'Amount'

        # Get value
        cell_coord = f"{column}{category_row}"
        value = self.get_cell_value(sheet_name, cell_coord, evaluated=True)

        # Get category name
        category_name = self.get_cell_value(sheet_name, f"A{category_row}", evaluated=True)

        return {
            'type': 'category_lookup',
            'category': category_name,
            'column': column_desc,
            'value': value,
            'cell': f"{sheet_name}!{cell_coord}"
        }

    def process_total_query(self, question: str) -> Optional[Dict[str, Any]]:
        """
        Process a query asking for totals.

        E.g., "What is my total monthly income?"

        Args:
            question: User's question

        Returns:
            Result dictionary or None
        """
        # Detect sheet
        sheet_name = self.detect_sheet(question)
        if not sheet_name:
            return None

        sheet_key = sheet_name.lower()
        sheet_info = self.sheet_index[sheet_key]

        # Look for "total" row (usually last row with data)
        total_row = None
        categories = sheet_info['categories']

        for row_num, cat_text in categories.items():
            if 'total' in cat_text:
                total_row = row_num
                break

        if not total_row:
            # Use last row with data
            total_row = sheet_info['max_row']

        # Determine column
        question_lower = question.lower()
        column = None
        column_desc = None

        if 'income' in question_lower:
            if 'monthly' in question_lower:
                column = self.find_column_by_header(sheet_name, 'monthly')
                column_desc = 'Monthly Income'
            elif 'annual' in question_lower or 'year' in question_lower:
                column = self.find_column_by_header(sheet_name, 'annual')
                column_desc = 'Annual Income'
            else:
                column = 'B'
                column_desc = 'Total Income'

        elif 'expense' in question_lower or 'spend' in question_lower:
            if 'budgeted' in question_lower or 'budget' in question_lower:
                column = self.find_column_by_header(sheet_name, 'budgeted')
                column_desc = 'Total Budgeted Expenses'
            elif 'actual' in question_lower:
                column = self.find_column_by_header(sheet_name, 'actual')
                column_desc = 'Total Actual Expenses'
            else:
                column = 'C'  # Default to actual
                column_desc = 'Total Expenses'
        else:
            column = 'B'
            column_desc = 'Total'

        # Get value
        cell_coord = f"{column}{total_row}"
        value = self.get_cell_value(sheet_name, cell_coord, evaluated=True)

        return {
            'type': 'total',
            'description': column_desc,
            'value': value,
            'cell': f"{sheet_name}!{cell_coord}"
        }

    def process_summary_query(self, question: str) -> Optional[Dict[str, Any]]:
        """
        Process queries about summary/dashboard metrics.

        E.g., "What is my savings rate?" or "What's my net income?"

        Args:
            question: User's question

        Returns:
            Result dictionary or None
        """
        # Find summary sheet
        summary_sheet = None
        for sheet_key in self.sheet_index:
            if 'summary' in sheet_key or 'dashboard' in sheet_key:
                summary_sheet = self.sheet_index[sheet_key]['name']
                break

        if not summary_sheet:
            return None

        question_lower = question.lower()

        # Map common summary queries to keywords
        query_keywords = {
            'savings rate': 'savings rate',
            'net income': 'net income',
            'budget performance': 'performance',
            'over budget': 'over',
            'under budget': 'under',
            'adherence': 'adherence'
        }

        # Find matching keyword
        matched_keyword = None
        for query, keyword in query_keywords.items():
            if query in question_lower:
                matched_keyword = keyword
                break

        if not matched_keyword:
            # Extract keywords from question
            keywords = self.extract_keywords(question)
            if keywords:
                matched_keyword = keywords[0]

        if not matched_keyword:
            return None

        # Find row with this keyword
        row = self.find_category_row(summary_sheet, matched_keyword)

        if not row:
            return None

        # Get value from column B (typical for summary sheets)
        value = self.get_cell_value(summary_sheet, f"B{row}", evaluated=True)
        label = self.get_cell_value(summary_sheet, f"A{row}", evaluated=True)

        return {
            'type': 'summary',
            'metric': label,
            'value': value,
            'cell': f"{summary_sheet}!B{row}"
        }

    def format_value(self, value: Any, number_format: str = None) -> str:
        """
        Format a value for display.

        Args:
            value: Value to format
            number_format: Excel number format string

        Returns:
            Formatted string
        """
        if value is None:
            return "N/A"

        if isinstance(value, (int, float)):
            # Check if it's currency
            if number_format and '$' in number_format:
                return f"${value:,.2f}"
            # Check if it's percentage
            elif number_format and '%' in number_format:
                return f"{value:.1%}"
            else:
                return f"{value:,.2f}" if isinstance(value, float) else f"{value:,}"

        return str(value)

    def format_answer(self, result: Dict[str, Any]) -> str:
        """
        Format result into natural language answer.

        Args:
            result: Result dictionary from query processing

        Returns:
            Formatted answer string
        """
        if not result:
            return "I couldn't find that information in the spreadsheet."

        result_type = result['type']

        if result_type == 'category_lookup':
            category = result['category']
            column = result['column']
            value = self.format_value(result['value'])
            cell = result['cell']

            return f"{category} ({column}): {value}\n\nSource: {cell}"

        elif result_type == 'total':
            description = result['description']
            value = self.format_value(result['value'])
            cell = result['cell']

            return f"{description}: {value}\n\nSource: {cell}"

        elif result_type == 'summary':
            metric = result['metric']
            value = self.format_value(result['value'])
            cell = result['cell']

            return f"{metric}: {value}\n\nSource: {cell}"

        return "Unable to format result"

    def calculate(self, question: str) -> Optional[str]:
        """
        Main entry point: process natural language question.

        Args:
            question: User's natural language question

        Returns:
            Formatted answer string, or None if not answerable
        """
        if not self.workbook:
            return "No spreadsheet loaded. Please load a spreadsheet first."

        # Detect query type
        query_type = self.detect_query_type(question)

        # Process based on type
        result = None

        if query_type == 'total':
            result = self.process_total_query(question)
        elif query_type == 'summary' or query_type == 'calculation':
            result = self.process_summary_query(question)
        elif query_type == 'category_lookup':
            result = self.process_category_lookup(question)

        # If no result yet, try other methods
        if not result:
            # Try category lookup as fallback
            result = self.process_category_lookup(question)

        if not result:
            # Try summary as fallback
            result = self.process_summary_query(question)

        # Format answer
        return self.format_answer(result)


# Example usage and testing
if __name__ == "__main__":
    from pathlib import Path

    # Path to budget planner
    budget_path = Path(__file__).parent.parent.parent / "datasets" / "spreadsheet" / "Budget_Planner.xlsx"

    if not budget_path.exists():
        print(f"Budget planner not found at: {budget_path}")
        print("Please run scripts/create_budget_planner.py first")
        exit(1)

    # Create calculator
    calc = SpreadsheetCalculator(str(budget_path))

    print("=" * 80)
    print("Budget Planner Query System - Test Cases")
    print("=" * 80)

    # Test queries
    test_questions = [
        # Income queries
        "What is my total monthly income?",
        "What is my total annual income?",
        "How much do I earn from salary?",
        "What's my freelance income?",

        # Expense queries
        "How much did I spend on groceries?",
        "What's my actual spending on transportation?",
        "What was budgeted for entertainment?",
        "How much is my rent?",

        # Summary queries
        "What is my savings rate?",
        "What's my net income?",
        "Am I over or under budget?",
        "What's my budget performance?",

        # Total queries
        "What are my total expenses?",
        "What's my total budgeted expenses?",
        "What's my total actual expenses?",
    ]

    for question in test_questions:
        answer = calc.calculate(question)
        print(f"\nQ: {question}")
        print(f"A: {answer}")
        print("-" * 80)
