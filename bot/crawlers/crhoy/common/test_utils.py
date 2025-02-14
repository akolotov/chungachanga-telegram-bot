"""Tests for utility functions."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

from .utils import get_trigger_time_info
from ..settings import settings

def test_trigger_times(trigger_times, test_times):
    """Test get_trigger_time_info with specific trigger times and test cases."""
    print(f"\nTesting with trigger times: {[t.strftime('%H:%M') for t in trigger_times]}")
    print("-" * 80)
    
    # Override settings trigger times for testing
    settings.notifier_trigger_times = trigger_times
    
    for test_time in test_times:
        result = get_trigger_time_info(test_time)
        print(f"Time: {test_time.strftime('%d.%m.%Y %H:%M:%S')}")
        print(f"  Previous: {result.previous.strftime('%d.%m.%Y %H:%M')}")
        print(f"  Current:  {result.current.strftime('%d.%m.%Y %H:%M')}")
        print(f"  Next:     {result.next.strftime('%d.%m.%Y %H:%M')}")
        print()

def run_tests():
    """Run tests with different trigger time configurations."""
    cr_tz = ZoneInfo("America/Costa_Rica")
    base_date = datetime(2025, 2, 13, tzinfo=cr_tz)  # 13.02.2025
    
    # Test case 1: Three trigger times [6:00, 12:00, 16:30]
    three_triggers = [time(6, 0), time(12, 0), time(16, 30)]
    test_times_three = [
        base_date.replace(hour=6, minute=0, second=0),   # 13.02.2025 06:00:00
        base_date.replace(hour=6, minute=0, second=1),   # 13.02.2025 06:00:01
        base_date.replace(hour=11, minute=59, second=59), # 13.02.2025 11:59:59
        base_date.replace(hour=12, minute=0, second=0),  # 13.02.2025 12:00:00
    ]
    test_trigger_times(three_triggers, test_times_three)
    
    # Test case 2: Single trigger time [09:00]
    single_trigger = [time(9, 0)]
    test_times_single = [
        base_date.replace(hour=6, minute=0, second=0),   # 13.02.2025 06:00:00
        base_date.replace(hour=10, minute=0, second=0),  # 13.02.2025 10:00:00
    ]
    test_trigger_times(single_trigger, test_times_single)
    
    # Test case 3: Two trigger times [09:00, 12:00]
    two_triggers = [time(9, 0), time(12, 0)]
    test_times_two = [
        base_date.replace(hour=6, minute=0, second=0),   # 13.02.2025 06:00:00
        base_date.replace(hour=10, minute=0, second=0),  # 13.02.2025 10:00:00
        base_date.replace(hour=18, minute=0, second=0),  # 13.02.2025 18:00:00
    ]
    test_trigger_times(two_triggers, test_times_two)

    # Test case 4: Five trigger times [8:00, 11:15, 15:45, 20:30, 23:55]
    five_triggers = [time(8, 0), time(11, 15), time(15, 45), time(20, 30), time(23, 55)]
    test_times_five = [
        base_date.replace(hour=0, minute=0, second=0),   # 13.02.2025 00:00:00 - before first trigger
        base_date.replace(hour=7, minute=59, second=59), # 13.02.2025 07:59:59 - just before first trigger
        base_date.replace(hour=8, minute=0, second=0),   # 13.02.2025 08:00:00 - at first trigger
        base_date.replace(hour=11, minute=14, second=59),# 13.02.2025 11:14:59 - just before second trigger
        base_date.replace(hour=11, minute=15, second=0), # 13.02.2025 11:15:00 - at second trigger
        base_date.replace(hour=15, minute=45, second=0), # 13.02.2025 15:45:00 - at third trigger
        base_date.replace(hour=20, minute=30, second=0), # 13.02.2025 20:30:00 - at fourth trigger
        base_date.replace(hour=23, minute=54, second=59),# 13.02.2025 23:54:59 - just before last trigger
        base_date.replace(hour=23, minute=55, second=0), # 13.02.2025 23:55:00 - at last trigger
        base_date.replace(hour=23, minute=59, second=59),# 13.02.2025 23:59:59 - after last trigger
    ]
    test_trigger_times(five_triggers, test_times_five)

if __name__ == "__main__":
    run_tests() 