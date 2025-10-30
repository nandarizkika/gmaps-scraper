"""
Example script for scraping warung kelontong in Jakarta Selatan

This script demonstrates how to use the scraper programmatically
to collect merchant data for all districts in Jakarta Selatan.

Usage:
    python example_jaksel.py

Output:
    - CSV file with pipe delimiter (|)
    - Excel file (.xlsx)
    - Files saved in results/ directory
"""
from config.settings import ScraperConfig
from core.orchestrator import ScraperOrchestrator
from utils.task_generator import TaskGenerator, JAKARTA_SELATAN_DISTRICTS


def main():
    """Main execution function"""
    
    print("="*70)
    print("WARUNG KELONTONG SCRAPER - JAKARTA SELATAN")
    print("="*70)
    
    
    
    config = ScraperConfig(
        headless=False,          
        max_workers=4,           
        scroll_pause_time=2.0,   
        max_scroll_attempts=10,  
        max_retries=3,           
        min_delay=1.0,           
        max_delay=2.5,           
        csv_delimiter="|"        
    )
    
    
    
    keywords = [
        "warung kelontong",
        "toko kelontong", 
        "minimarket",
        "toko sembako",
        "warung sembako"
    ]
    
    
    print(f"\n📍 Target area: Jakarta Selatan")
    print(f"📝 Keywords: {', '.join(keywords)}")
    print(f"🏘️  Districts: {len(JAKARTA_SELATAN_DISTRICTS)}")
    print(f"\nGenerating search tasks...")
    
    tasks = TaskGenerator.generate_district_tasks(
        keywords=keywords,
        city="Jakarta Selatan",
        districts=JAKARTA_SELATAN_DISTRICTS,
        max_results_per_task=30  
    )
    
    print(f"\n✅ Generated {len(tasks)} search tasks")
    print(f"   • Keywords: {len(keywords)}")
    print(f"   • Districts: {len(JAKARTA_SELATAN_DISTRICTS)}")
    print(f"   • Combinations: {len(keywords)} × {len(JAKARTA_SELATAN_DISTRICTS)} = {len(tasks)}")
    
    
    estimated_time = (len(tasks) * 15) / config.max_workers  
    print(f"\n⏱️  Estimated time: {estimated_time/60:.1f} minutes")
    print(f"   (with {config.max_workers} parallel workers)")
    
    
    print("\n" + "="*70)
    response = input("Start scraping? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    
    orchestrator = ScraperOrchestrator(config)
    
    try:
        
        print("\n🚀 Starting scraper...\n")
        df = orchestrator.scrape_tasks(tasks)
        
        
        if not df.empty:
            print(f"\n✅ Success! Collected {len(df)} unique places")
            orchestrator.save_results(df, prefix="warung_kelontong_jaksel")
            print("\n📁 Results saved in 'results/' directory")
        else:
            print("\n⚠️  No results collected")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Scraping interrupted by user (Ctrl+C)")
        print("💾 Saving partial results...")
        
        
        if orchestrator.results:
            df = orchestrator._create_dataframe()
            if not df.empty:
                orchestrator.save_results(df, prefix="warung_kelontong_jaksel_partial")
                print(f"✅ Saved {len(df)} partial results")
            else:
                print("⚠️  No results to save")
        else:
            print("⚠️  No results collected yet")
    
    except Exception as e:
        print(f"\n❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        
        
        if orchestrator.results:
            print("\n💾 Attempting to save partial results...")
            try:
                df = orchestrator._create_dataframe()
                if not df.empty:
                    orchestrator.save_results(df, prefix="warung_kelontong_jaksel_error")
                    print(f"✅ Saved {len(df)} results before error")
            except Exception as save_error:
                print(f"❌ Could not save results: {save_error}")
    
    print("\n" + "="*70)
    print("SCRAPING COMPLETED")
    print("="*70)


if __name__ == "__main__":
    main()