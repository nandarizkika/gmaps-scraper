"""
Merge all task CSV files into one combined file
Useful if you want to combine 120 individual task files
"""
import os
import pandas as pd
from glob import glob
from datetime import datetime

def merge_task_files(results_dir='results', output_file=None):
    """
    Merge all task_XXX_*.csv files into one combined CSV
    
    Args:
        results_dir: Directory containing task CSV files
        output_file: Output filename (auto-generated if None)
    """
    print("=" * 80)
    print("MERGING TASK FILES")
    print("=" * 80)
    
    # Find all task files
    pattern = os.path.join(results_dir, 'task_*.csv')
    task_files = sorted(glob(pattern))
    
    if not task_files:
        print(f"❌ No task files found in {results_dir}")
        return
    
    print(f"\n📁 Found {len(task_files)} task files")
    
    # Read and combine all files
    dfs = []
    total_places = 0
    
    for i, file in enumerate(task_files, 1):
        try:
            df = pd.read_csv(file, sep='|')
            dfs.append(df)
            total_places += len(df)
            print(f"  [{i}/{len(task_files)}] ✓ {os.path.basename(file)} ({len(df)} places)")
        except Exception as e:
            print(f"  [{i}/{len(task_files)}] ❌ {os.path.basename(file)} - Error: {e}")
    
    if not dfs:
        print("\n❌ No valid data found")
        return
    
    # Combine all DataFrames
    print(f"\n🔄 Combining {len(dfs)} files...")
    combined_df = pd.concat(dfs, ignore_index=True)
    
    # Generate output filename
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(results_dir, f"merged_results_{timestamp}.csv")
    
    # Save combined file
    combined_df.to_csv(output_file, index=False, sep='|')
    
    # Also save as Excel
    excel_file = output_file.replace('.csv', '.xlsx')
    combined_df.to_excel(excel_file, index=False, engine='openpyxl')
    
    print("\n" + "=" * 80)
    print("✅ MERGE COMPLETE!")
    print("=" * 80)
    print(f"📊 Statistics:")
    print(f"  - Task files processed: {len(dfs)}")
    print(f"  - Total places: {total_places}")
    print(f"  - Unique places: {len(combined_df)}")
    print(f"\n💾 Output files:")
    print(f"  - CSV:   {output_file}")
    print(f"  - Excel: {excel_file}")
    print("=" * 80)
    
    return combined_df


def cleanup_task_files(results_dir='results', keep_merged=True):
    """
    Clean up individual task files after merging
    
    Args:
        results_dir: Directory containing task files
        keep_merged: Keep the merged file
    """
    print("\n🗑️  Cleaning up task files...")
    
    pattern = os.path.join(results_dir, 'task_*.csv')
    task_files = glob(pattern)
    
    for file in task_files:
        try:
            os.remove(file)
            print(f"  ✓ Deleted: {os.path.basename(file)}")
        except Exception as e:
            print(f"  ❌ Error deleting {file}: {e}")
    
    print(f"\n✅ Cleaned up {len(task_files)} task files")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Merge task CSV files')
    parser.add_argument('--dir', default='results', help='Results directory')
    parser.add_argument('--output', help='Output filename')
    parser.add_argument('--cleanup', action='store_true', help='Delete task files after merge')
    
    args = parser.parse_args()
    
    # Merge files
    df = merge_task_files(args.dir, args.output)
    
    # Cleanup if requested
    if df is not None and args.cleanup:
        response = input("\n⚠️  Delete all task files? (yes/no): ")
        if response.lower() == 'yes':
            cleanup_task_files(args.dir)
        else:
            print("Skipped cleanup")