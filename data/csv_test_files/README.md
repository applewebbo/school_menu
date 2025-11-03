# CSV Test Files for Manual Testing

This directory contains various CSV files for manually testing the CSV upload functionality and error handling. Each file is designed to test specific edge cases and error scenarios.

## Test Files Overview

### ❌ Expected to FAIL (Error Handling Tests)

#### 01_unclosed_quotes.csv
**Issue:** Contains an unclosed quote in the "pranzo" field
**Expected Error:** "Il file CSV contiene virgolette o delimitatori non validi. Verifica che tutte le virgolette siano chiuse correttamente."
**Tests:** Quote validation and proper error messaging

#### 02_missing_required_columns.csv
**Issue:** Missing required columns "spuntino" and "merenda"
**Expected Error:** "Il file non contiene tutte le colonne richieste. Colonne mancanti: spuntino, merenda"
**Tests:** Required column validation

#### 03_wrong_day_names.csv
**Issue:** Contains invalid day names (Lun, Mar, Wednesday instead of Lunedì, Martedì, etc.)
**Expected Error:** 'Formato non valido. La colonna "giorno" contiene valori diversi dai giorni della settimana.'
**Tests:** Day name validation (must be Italian full day names)

#### 04_wrong_week_numbers.csv
**Issue:** Contains week numbers outside valid range (5, 0, -1 instead of 1-4)
**Expected Error:** 'Formato non valido. La colonna "settimana" contiene valori non compresi fra 1 e 4.'
**Tests:** Week number range validation

#### 08_non_integer_week.csv
**Issue:** Contains non-integer values in settimana column (prima, seconda, abc)
**Expected Error:** 'Formato non valido. La colonna "settimana" contiene valori non numerici.'
**Tests:** Week column data type validation

#### 09_annual_malformed_dates.csv
**Issue:** Contains various malformed dates (32/01/2024, 01-01-2024, 2024/01/15, 15/13/2024)
**Expected Error:** 'Formato non valido. La colonna "data" contiene date in formato non valido. Usa il formato GG/MM/AAAA'
**Tests:** Annual menu date format validation (must be DD/MM/YYYY)

#### 10_empty_file.csv
**Issue:** Completely empty file
**Expected Error:** CSV parsing error or invalid dimensions error
**Tests:** Empty file handling

#### 11_only_headers.csv
**Issue:** Contains only headers, no data rows
**Expected Error:** May succeed but import 0 rows, or fail with validation error
**Tests:** Empty dataset handling

#### 06_mixed_delimiters.csv
**Issue:** Mixes commas and semicolons inconsistently
**Expected Error:** CSV parsing error or incorrect field parsing
**Tests:** Delimiter detection with inconsistent data

#### 07_tab_delimiter.csv
**Issue:** Uses tab character as delimiter (not supported - only comma and semicolon)
**Expected Error:** May parse incorrectly or fail validation
**Tests:** Unsupported delimiter handling

#### 13_single_quotes.csv
**Issue:** Uses single quotes instead of double quotes
**Expected Error:** May parse as literal single quotes in data
**Tests:** Quote character validation (only double quotes are standard CSV)

---

### ✅ Expected to SUCCEED (Flexibility Tests)

#### 05_extra_trailing_columns.csv
**Should Work:** Contains extra unnamed columns and named columns not in schema
**Tests:** Column filtering removes unnamed and extra columns
**Expected Behavior:** Successfully imports with only valid columns

#### 12_whitespace_columns.csv
**Should Work:** Contains columns with whitespace-only names
**Tests:** Column filtering removes whitespace-only column names
**Expected Behavior:** Successfully imports with only valid columns

#### 14_detailed_semicolon_good.csv
**Should Work:** Valid detailed menu with semicolon delimiter
**Tests:** Semicolon delimiter detection and parsing
**Expected Behavior:** Successfully imports all rows with detected `;` delimiter

#### 15_quoted_with_commas_good.csv
**Should Work:** Quoted fields containing commas
**Tests:** Proper quote handling preserves commas within fields
**Expected Behavior:** Successfully imports with commas preserved in field values

#### 16_extra_columns_should_work.csv
**Should Work:** Contains extra named columns (note, allergie, extra)
**Tests:** Column filtering ignores extra named columns
**Expected Behavior:** Successfully imports with only required columns

#### 17_bom_encoding.csv
**Should Work:** Standard UTF-8 file
**Tests:** Basic encoding handling
**Expected Behavior:** Successfully imports

#### 18_annual_good.csv
**Should Work:** Valid annual menu with proper date format (DD/MM/YYYY)
**Tests:** Annual menu date parsing
**Expected Behavior:** Successfully imports all dates

---

## How to Use These Test Files

### Manual Testing via Web Interface

1. Navigate to the menu upload page in the application
2. Select the menu type (Simple, Detailed, or Annual)
3. Upload one of these test files
4. Verify the expected behavior:
   - **For FAIL files:** Check that the appropriate error message is displayed
   - **For SUCCEED files:** Check that the import completes successfully

### Testing Coverage

These files test the following aspects of the CSV upload feature:

- ✅ **Delimiter Detection:** Comma (`,`) and semicolon (`;`) support
- ✅ **Column Filtering:** Unnamed, whitespace-only, and extra columns
- ✅ **Quote Handling:** Double quotes with embedded delimiters
- ✅ **Validation:** Day names, week numbers, date formats
- ✅ **Error Messages:** Clear, specific, actionable error messages
- ✅ **Edge Cases:** Empty files, headers-only, encoding issues

---

## Expected Column Names

### Simple Menu (settimana-based)
- `giorno` - Day of week (Lunedì, Martedì, Mercoledì, Giovedì, Venerdì)
- `settimana` - Week number (1-4)
- `pranzo` - Lunch menu
- `spuntino` - Morning snack
- `merenda` - Afternoon snack

### Detailed Menu (settimana-based)
- `giorno` - Day of week (Lunedì, Martedì, Mercoledì, Giovedì, Venerdì)
- `settimana` - Week number (1-4)
- `primo` - First course
- `secondo` - Second course
- `contorno` - Side dish
- `frutta` - Fruit
- `spuntino` - Snack

### Annual Menu (date-based)
- `data` - Date in DD/MM/YYYY format
- `primo` - First course
- `secondo` - Second course
- `contorno` - Side dish
- `frutta` - Fruit
- `altro` - Other/Additional

---

---

### 🔄 Menu Type Mismatch Detection (Should FAIL with helpful message)

#### 19_simple_instead_of_detailed.csv
**Issue:** Simple menu uploaded when detailed menu selected
**Expected Error:** "Il file caricato sembra essere un Menu Semplice, ma hai selezionato Menu Dettagliato. Verifica di aver caricato il file corretto."
**Tests:** Menu type detection (simple vs detailed)
**How to Test:** Upload this file when creating/uploading a Detailed Menu

#### 20_detailed_instead_of_simple.csv
**Issue:** Detailed menu uploaded when simple menu selected
**Expected Error:** "Il file caricato sembra essere un Menu Dettagliato, ma hai selezionato Menu Semplice. Verifica di aver caricato il file corretto."
**Tests:** Menu type detection (detailed vs simple)
**How to Test:** Upload this file when creating/uploading a Simple Menu

#### 21_annual_instead_of_weekly.csv
**Issue:** Annual menu uploaded when weekly menu (simple or detailed) selected
**Expected Error:** "Il file caricato sembra essere un Menu Annuale, ma hai selezionato Menu [Semplice/Dettagliato]. Verifica di aver caricato il file corretto."
**Tests:** Menu type detection (annual vs weekly)
**How to Test:** Upload this file when creating/uploading a Simple or Detailed Menu

#### 22_weekly_instead_of_annual_simple.csv
**Issue:** Simple weekly menu uploaded when annual menu selected
**Expected Error:** "Il file caricato sembra essere un Menu Semplice (con settimane), ma hai selezionato Menu Annuale. Verifica di aver caricato il file corretto."
**Tests:** Menu type detection (simple weekly vs annual)
**How to Test:** Upload this file when creating/uploading an Annual Menu

#### 23_weekly_instead_of_annual_detailed.csv
**Issue:** Detailed weekly menu uploaded when annual menu selected
**Expected Error:** "Il file caricato sembra essere un Menu Dettagliato (con settimane), ma hai selezionato Menu Annuale. Verifica di aver caricato il file corretto."
**Tests:** Menu type detection (detailed weekly vs annual)
**How to Test:** Upload this file when creating/uploading an Annual Menu

---

## Issue Reference

These test files support the implementation of issue #186: "Flexible CSV Upload"
- Accept `,` (comma) or `;` (semicolon) as delimiter
- Accept blank columns and don't import them
- Accept quotes (proper handling of quoted fields)
- Detect menu type mismatch and provide helpful error messages
