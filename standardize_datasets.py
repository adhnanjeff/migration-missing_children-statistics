#!/usr/bin/env python3
"""
Dataset Standardization Script
Standardizes all datasets to common schema:
- state
- district
- time (YYYY-MM or YYYY)
- metric_type
- value
- source
"""

import pandas as pd
import os
from datetime import datetime
import re

# Create output directory
os.makedirs('Standardized_Data', exist_ok=True)

def standardize_date(date_str):
    """Convert date string to YYYY-MM format"""
    try:
        # Handle DD-MM-YYYY format
        if isinstance(date_str, str) and '-' in date_str:
            parts = date_str.split('-')
            if len(parts) == 3:
                day, month, year = parts
                return f"{year}-{month.zfill(2)}"
        # Handle other formats if needed
        return date_str
    except:
        return date_str

def clean_district_name(district):
    """Clean and standardize district names"""
    if pd.isna(district):
        return None
    district = str(district).strip()
    
    # Remove common prefixes
    district = re.sub(r'^District\s*-\s*', '', district, flags=re.IGNORECASE)
    district = re.sub(r'\s*\d+\s*$', '', district)  # Remove trailing numbers
    district = district.strip()
    
    # Remove asterisks and extra whitespace
    district = re.sub(r'\*+', '', district)
    district = ' '.join(district.split())  # Normalize whitespace
    
    # Common fixes
    replacements = {
        'Bangalore': 'Bengaluru',
        'Trichirappalli': 'Tiruchirappalli',
        'Tuticorin': 'Thoothukudi',
        'Bellary': 'Ballari',
        'Gulbarga': 'Kalaburagi',  # Official name change
        'Mysore': 'Mysuru',
    }
    for old, new in replacements.items():
        if old in district:
            district = district.replace(old, new)
    
    return district

def process_aadhaar_demographic(file_path, state_name, output_file):
    """Process Aadhaar Demographic Monthly Update data"""
    print(f"\nProcessing {file_path}...")
    
    df = pd.read_csv(file_path)
    print(f"  Original shape: {df.shape}")
    print(f"  Columns: {df.columns.tolist()}")
    
    # Aggregate by state, district, and date (month)
    # Sum all demographic update columns
    demo_cols = [col for col in df.columns if 'demo' in col.lower()]
    
    if not demo_cols:
        print(f"  WARNING: No demographic columns found!")
        return None
    
    # Group by date, state, district and sum values
    df['time'] = df['date'].apply(standardize_date)
    df['district'] = df['district'].apply(clean_district_name)
    
    # Sum all demographic columns
    df['total_updates'] = df[demo_cols].sum(axis=1)
    
    # Aggregate by state, district, time
    aggregated = df.groupby(['state', 'district', 'time']).agg({
        'total_updates': 'sum'
    }).reset_index()
    
    # Create standardized format
    standardized = pd.DataFrame({
        'state': aggregated['state'],
        'district': aggregated['district'],
        'time': aggregated['time'],
        'metric_type': 'aadhaar_demographic_update',
        'value': aggregated['total_updates'],
        'source': 'UIDAI'
    })
    
    # Remove rows with null districts
    standardized = standardized.dropna(subset=['district', 'state'])
    
    print(f"  Standardized shape: {standardized.shape}")
    standardized.to_csv(output_file, index=False)
    print(f"  Saved to {output_file}")
    
    return standardized

def process_aadhaar_biometric(file_path, state_name, output_file):
    """Process Aadhaar Biometric Monthly Update data"""
    print(f"\nProcessing {file_path}...")
    
    df = pd.read_csv(file_path)
    print(f"  Original shape: {df.shape}")
    print(f"  Columns: {df.columns.tolist()}")
    
    # Aggregate by state, district, and date (month)
    bio_cols = [col for col in df.columns if 'bio' in col.lower()]
    
    if not bio_cols:
        print(f"  WARNING: No biometric columns found!")
        return None
    
    # Group by date, state, district and sum values
    df['time'] = df['date'].apply(standardize_date)
    df['district'] = df['district'].apply(clean_district_name)
    
    # Sum all biometric columns
    df['total_updates'] = df[bio_cols].sum(axis=1)
    
    # Aggregate by state, district, time
    aggregated = df.groupby(['state', 'district', 'time']).agg({
        'total_updates': 'sum'
    }).reset_index()
    
    # Create standardized format
    standardized = pd.DataFrame({
        'state': aggregated['state'],
        'district': aggregated['district'],
        'time': aggregated['time'],
        'metric_type': 'aadhaar_biometric_update',
        'value': aggregated['total_updates'],
        'source': 'UIDAI'
    })
    
    # Remove rows with null districts
    standardized = standardized.dropna(subset=['district', 'state'])
    
    print(f"  Standardized shape: {standardized.shape}")
    standardized.to_csv(output_file, index=False)
    print(f"  Saved to {output_file}")
    
    return standardized

def process_census_migration(file_path, state_name, output_file):
    """Process Census D-02 Migration data"""
    print(f"\nProcessing {file_path}...")
    
    # Read Excel file without header to access raw structure
    df = pd.read_excel(file_path, header=None)
    print(f"  Original shape: {df.shape}")
    
    # Structure: Row 1 has headers, Row 4+ has data
    # Columns: 0=Table, 1=State, 2=District, 3=Area Name, 7=Total migrants (Persons)
    
    result_data = []
    seen_districts = set()
    
    # Process each row starting from row 4 (0-indexed)
    for idx in range(4, len(df)):
        row = df.iloc[idx]
        
        # Check if this is a district row (not state total)
        table_code = row.iloc[0] if len(row) > 0 else None
        state_code = row.iloc[1] if len(row) > 1 else None
        dist_code = row.iloc[2] if len(row) > 2 else None
        area_name = row.iloc[3] if len(row) > 3 else None
        total_migrants = row.iloc[7] if len(row) > 7 else None
        
        # Skip if not a valid data row
        if pd.isna(table_code) or str(table_code).strip() == '':
            continue
        
        # Skip state totals (district code '00' or 0)
        dist_code_str = str(dist_code).strip() if pd.notna(dist_code) else ''
        if dist_code_str in ['00', '0', '']:
            continue
        
        # Skip if area name contains "STATE" (state totals)
        if pd.notna(area_name) and 'STATE' in str(area_name).upper():
            continue
        
        # We want the "Total" row for each district (column 4 = 'Total', column 5 = 'Total', column 6 = 'Total')
        # This gives us the total migrants for the district
        col4 = row.iloc[4] if len(row) > 4 else None
        col5 = row.iloc[5] if len(row) > 5 else None
        col6 = row.iloc[6] if len(row) > 6 else None
        
        # Look for the row where all three are 'Total' - this is district total
        if (str(col4).strip() == 'Total' and 
            str(col5).strip() == 'Total' and 
            str(col6).strip() == 'Total'):
            
            district = clean_district_name(area_name)
            
            if district and pd.notna(total_migrants):
                # Avoid duplicates - use district code as key
                district_key = f"{state_code}_{dist_code_str}"
                if district_key not in seen_districts:
                    seen_districts.add(district_key)
                    try:
                        migrant_count = float(total_migrants)
                        if migrant_count > 0:
                            result_data.append({
                                'state': state_name,
                                'district': district,
                                'time': '2011',
                                'metric_type': 'census_migration',
                                'value': migrant_count,
                                'source': 'Census 2011'
                            })
                    except (ValueError, TypeError):
                        pass
    
    standardized = pd.DataFrame(result_data)
    
    # Remove rows with null districts
    standardized = standardized.dropna(subset=['district', 'state'])
    
    print(f"  Standardized shape: {standardized.shape}")
    if len(standardized) > 0:
        print(f"  Sample districts: {standardized['district'].head(5).tolist()}")
    standardized.to_csv(output_file, index=False)
    print(f"  Saved to {output_file}")
    
    return standardized

def process_census_population(file_path, output_file):
    """Process Census PCA Population data"""
    print(f"\nProcessing {file_path}...")
    
    df = pd.read_excel(file_path)
    print(f"  Original shape: {df.shape}")
    print(f"  Columns: {df.columns.tolist()}")
    
    # This file appears to have age-group data, not district-level
    # We need to extract only district totals (where Age is 'All ages' or similar)
    # Columns: Table, State, Distt., Area Name, Age, Total Persons, ...
    
    result_data = []
    
    # Look for rows with district codes (not 0 or 00) and age = 'All ages' or total
    for _, row in df.iterrows():
        state_code = row.get('State', None)
        dist_code = row.get('Distt.', None)
        area_name = row.get('Area Name', None)
        age = row.get('Age', None)
        total_persons = row.get('Total Persons', None)
        
        # Skip if missing key fields
        if pd.isna(dist_code) or pd.isna(area_name) or pd.isna(total_persons):
            continue
        
        # Skip state/country totals (district code 0 or 00)
        dist_code_str = str(dist_code).strip()
        if dist_code_str in ['0', '00', '']:
            continue
        
        # Only get total population (all ages) - skip age-specific rows
        age_str = str(age).strip().lower() if pd.notna(age) else ''
        if 'all' not in age_str and 'total' not in age_str and age_str != '':
            continue
        
        # Skip if area name is just "India" or state name
        area_str = str(area_name).strip()
        if area_str.upper() in ['INDIA', 'TOTAL']:
            continue
        
        # Check if this looks like a district name (not a state name)
        # District names usually don't contain "STATE" or are very short
        if 'STATE' in area_str.upper() and len(area_str.split()) <= 3:
            continue
        
        district = clean_district_name(area_name)
        if district and len(district) > 2:  # Valid district name
            try:
                pop_count = float(total_persons)
                if pop_count > 0:
                    # Try to determine state from state code
                    # For now, we'll use a simple approach - state code mapping
                    # State codes: 29=Karnataka, 33=Tamil Nadu, etc.
                    state_code_int = int(state_code) if pd.notna(state_code) else None
                    state_map = {
                        29: 'Karnataka',
                        33: 'Tamil Nadu',
                    }
                    state = state_map.get(state_code_int, 'India')
                    
                    result_data.append({
                        'state': state,
                        'district': district,
                        'time': '2011',
                        'metric_type': 'population',
                        'value': pop_count,
                        'source': 'Census 2011 PCA'
                    })
            except (ValueError, TypeError):
                pass
    
    standardized = pd.DataFrame(result_data)
    
    if len(standardized) == 0:
        print(f"  WARNING: No data extracted. File structure may be different.")
        return None
    
    standardized = standardized.dropna(subset=['district', 'state'])
    
    # Remove duplicates (keep first occurrence)
    standardized = standardized.drop_duplicates(subset=['district', 'state', 'time'], keep='first')
    
    print(f"  Standardized shape: {standardized.shape}")
    if len(standardized) > 0:
        print(f"  Sample districts: {standardized['district'].head(5).tolist()}")
    standardized.to_csv(output_file, index=False)
    print(f"  Saved to {output_file}")
    
    return standardized

def create_district_mapping(all_datasets):
    """Create district name mapping file"""
    print("\n" + "="*60)
    print("Creating District Name Mapping...")
    print("="*60)
    
    all_districts = set()
    for df in all_datasets:
        if df is not None and 'district' in df.columns:
            all_districts.update(df['district'].dropna().unique())
    
    # Create mapping (raw_name -> standard_name)
    # For now, use cleaned names as standard
    mapping_data = []
    for district in sorted(all_districts):
        standard = clean_district_name(district)
        if standard != district:
            mapping_data.append({
                'raw_name': district,
                'standard_name': standard
            })
    
    if mapping_data:
        mapping_df = pd.DataFrame(mapping_data)
        mapping_df.to_csv('Standardized_Data/district_mapping.csv', index=False)
        print(f"Created district mapping with {len(mapping_data)} entries")
    else:
        print("No district name variations found (all already standardized)")
    
    return all_districts

def validate_datasets(all_datasets):
    """Validate all standardized datasets"""
    print("\n" + "="*60)
    print("VALIDATION REPORT")
    print("="*60)
    
    required_columns = ['state', 'district', 'time', 'metric_type', 'value', 'source']
    all_valid = True
    
    for i, df in enumerate(all_datasets):
        if df is None:
            continue
            
        print(f"\nDataset {i+1}:")
        print(f"  Shape: {df.shape}")
        
        # Check required columns
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            print(f"  ❌ MISSING COLUMNS: {missing_cols}")
            all_valid = False
        else:
            print(f"  ✅ All required columns present")
        
        # Check for null districts/states
        null_districts = df['district'].isna().sum()
        null_states = df['state'].isna().sum()
        if null_districts > 0 or null_states > 0:
            print(f"  ❌ NULL VALUES: {null_districts} null districts, {null_states} null states")
            all_valid = False
        else:
            print(f"  ✅ No null districts or states")
        
        # Check time format
        time_format_ok = True
        for time_val in df['time'].unique()[:10]:  # Check first 10
            if not (str(time_val).startswith('2011') or '-' in str(time_val)):
                time_format_ok = False
                break
        if time_format_ok:
            print(f"  ✅ Time format looks correct")
        else:
            print(f"  ⚠️  Time format may need review")
    
    if all_valid:
        print("\n✅ ALL VALIDATIONS PASSED!")
    else:
        print("\n❌ SOME VALIDATIONS FAILED - Please review")
    
    return all_valid

def main():
    print("="*60)
    print("DATASET STANDARDIZATION")
    print("="*60)
    
    all_datasets = []
    
    # Process Aadhaar Demographic data
    demo_tn = process_aadhaar_demographic(
        'Raw_Data/DemographicTN.csv',
        'Tamil Nadu',
        'Standardized_Data/aadhaar_demographic_tn.csv'
    )
    all_datasets.append(demo_tn)
    
    # Process Aadhaar Biometric data
    bio_tn = process_aadhaar_biometric(
        'Raw_Data/BiometricTN.csv',
        'Tamil Nadu',
        'Standardized_Data/aadhaar_biometric_tn.csv'
    )
    all_datasets.append(bio_tn)
    
    # Note: BiometricKarnataka.csv seems to have demographic columns, not biometric
    # Process it as demographic if needed
    bio_ka = process_aadhaar_demographic(
        'Raw_Data/BiometricKarnataka.csv',
        'Karnataka',
        'Standardized_Data/aadhaar_demographic_ka.csv'
    )
    all_datasets.append(bio_ka)
    
    # Note: Census Migration datasets (Census_TN.xls and Census_Karnataka.xls) 
    # are not used in this analysis
    
    # Note: Census Population data should be fetched from API using fetch_census_api.py
    # The Census_India.xls file only contains India-level data, not district-level
    # Run: python3 fetch_census_api.py YOUR_API_KEY
    # This will create Standardized_Data/census_population_api.csv
    
    # Create district mapping
    all_districts = create_district_mapping(all_datasets)
    
    # Combine all datasets
    combined = pd.concat([df for df in all_datasets if df is not None], ignore_index=True)
    combined.to_csv('Standardized_Data/combined_standardized.csv', index=False)
    print(f"\n✅ Combined dataset saved: {combined.shape}")
    
    # Validate
    validate_datasets(all_datasets)
    
    print("\n" + "="*60)
    print("STANDARDIZATION COMPLETE!")
    print("="*60)

if __name__ == '__main__':
    main()
