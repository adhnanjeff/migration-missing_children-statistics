#!/usr/bin/env python3
"""Create comprehensive district mapping from all standardized datasets"""
import pandas as pd
import os

def create_district_mapping():
    """Create district name mapping file"""
    print("="*60)
    print("Creating District Name Mapping")
    print("="*60)
    
    # Load all standardized datasets
    datasets = []
    files = [
        'Standardized_Data/aadhaar_demographic_tn.csv',
        'Standardized_Data/aadhaar_biometric_tn.csv',
        'Standardized_Data/aadhaar_demographic_ka.csv',
        'Standardized_Data/census_migration_tn.csv',
        'Standardized_Data/census_migration_ka.csv',
    ]
    
    all_districts = {}
    
    for file in files:
        if os.path.exists(file):
            df = pd.read_csv(file)
            if 'district' in df.columns and 'state' in df.columns:
                for _, row in df.iterrows():
                    state = row['state']
                    district = row['district']
                    if pd.notna(district) and pd.notna(state):
                        key = (state, district)
                        if key not in all_districts:
                            all_districts[key] = {
                                'state': state,
                                'district': district,
                                'sources': []
                            }
                        all_districts[key]['sources'].append(file.split('/')[-1])
    
    # Create mapping DataFrame
    mapping_data = []
    for (state, district), info in sorted(all_districts.items()):
        mapping_data.append({
            'state': state,
            'district': district,
            'sources': ', '.join(set(info['sources']))
        })
    
    mapping_df = pd.DataFrame(mapping_data)
    mapping_df.to_csv('Standardized_Data/district_master_list.csv', index=False)
    
    print(f"\n✅ Created district master list with {len(mapping_df)} unique districts")
    print(f"\nBy State:")
    print(mapping_df['state'].value_counts())
    
    # Check for potential name variations
    print(f"\nChecking for district name variations...")
    districts_by_state = {}
    for state in mapping_df['state'].unique():
        state_districts = mapping_df[mapping_df['state'] == state]['district'].tolist()
        districts_by_state[state] = state_districts
    
    # Look for similar names (simple check)
    variations = []
    for state, districts in districts_by_state.items():
        for i, d1 in enumerate(districts):
            for d2 in districts[i+1:]:
                # Check if names are very similar (fuzzy match)
                d1_lower = d1.lower().replace(' ', '')
                d2_lower = d2.lower().replace(' ', '')
                if d1_lower != d2_lower and (d1_lower in d2_lower or d2_lower in d1_lower):
                    if len(d1_lower) > 5 and len(d2_lower) > 5:  # Ignore very short matches
                        variations.append({
                            'state': state,
                            'district1': d1,
                            'district2': d2
                        })
    
    if variations:
        var_df = pd.DataFrame(variations)
        var_df.to_csv('Standardized_Data/district_name_variations.csv', index=False)
        print(f"⚠️  Found {len(variations)} potential name variations (saved to district_name_variations.csv)")
    else:
        print("✅ No obvious name variations found")
    
    return mapping_df

if __name__ == '__main__':
    create_district_mapping()
