#!/usr/bin/env python
"""
Test script for the rewritten parser
"""
import sys
import os
sys.path.append('wushu_analytics')

from wushu_analytics.main.DataController.parser import parse_competitions, parse_competition_detail

def test_competition_list_parser():
    """Test the competition list parser"""
    print("=== Testing Competition List Parser ===")
    try:
        competitions = parse_competitions()
        print(f"✓ Successfully parsed {len(competitions)} competitions")
        
        if competitions:
            print("First competition:")
            comp = competitions[0]
            print(f"  Name: {comp['name']}")
            print(f"  City: {comp['city']}")
            print(f"  Dates: {comp['start_date']} - {comp['end_date']}")
            print(f"  Link: {comp['link']}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_competition_detail_parser():
    """Test the competition detail parser"""
    print("\n=== Testing Competition Detail Parser ===")
    try:
        # Use the example URL from the requirements
        test_url = "https://wushujudges.ru/site/competition/218"
        detail_data = parse_competition_detail(test_url)
        
        if detail_data:
            print(f"✓ Successfully parsed competition: {detail_data['name']}")
            print(f"  Found {len(detail_data['carpets'])} carpets")
            
            for carpet in detail_data['carpets']:
                print(f"  Carpet {carpet['carpet_number']}: {len(carpet['category_blocks'])} category blocks")
                
                for block in carpet['category_blocks'][:2]:  # Show first 2 blocks
                    print(f"    - {block['category_name']}")
                    print(f"      Status: {block['status']}")
                    print(f"      Participants: {len(block['participants'])}")
                    if block['participants']:
                        participant = block['participants'][0]
                        print(f"      Sample participant: {participant['name']} ({participant['region']})")
            
            return True
        else:
            print("✗ No data returned")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("Parser Test Suite")
    print("=" * 50)
    
    success = True
    
    # Test competition list parser
    if not test_competition_list_parser():
        success = False
    
    # Test competition detail parser
    if not test_competition_detail_parser():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed!")
    
    return success

if __name__ == "__main__":
    main()
