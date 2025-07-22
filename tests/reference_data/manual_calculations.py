"""Manual calculations for mathematical validation.

Hand-verified reference data for deterministic validation of core indicators.
All calculations manually verified for small datasets.

Following KISS principle: minimal reference data, hand-calculated for confidence.
"""

# ATR Test Cases - Hand-calculated reference values
ATR_TEST_CASES = {
    "simple_case": {
        "description": "5-day OHLC with easy-to-verify True Range calculations",
        "ohlc": {
            'open':  [100, 103, 106, 107, 110],
            'high':  [105, 108, 109, 112, 113], 
            'low':   [98,  101, 104, 105, 108],
            'close': [103, 106, 107, 110, 111]
        },
        "expected_true_ranges": [7.0, 7.0, 5.0, 7.0, 5.0],  # Hand-calculated TR for each day
        "expected_atr_period_3": {
            "day_3": 6.33,  # (7+7+5)/3 = 6.33
            "day_4": 6.55,  # (6.33*2+7)/3 = 6.55  
            "day_5": 6.03   # (6.55*2+5)/3 = 6.03
        },
        "calculation_notes": [
            "Day 1: TR = High-Low = 105-98 = 7 (no previous close)",
            "Day 2: TR = max(108-101, |108-103|, |101-103|) = max(7, 5, 2) = 7",
            "Day 3: TR = max(109-104, |109-106|, |104-106|) = max(5, 3, 2) = 5",
            "Day 4: TR = max(112-105, |112-107|, |105-107|) = max(7, 5, 2) = 7", 
            "Day 5: TR = max(113-108, |113-110|, |108-110|) = max(5, 3, 2) = 5",
            "ATR uses Wilder's smoothing: ATR_new = (ATR_prev * (n-1) + TR_current) / n"
        ]
    },
    
    "zero_volatility": {
        "description": "Constant prices - should result in zero ATR",
        "ohlc": {
            'high': [100, 100, 100, 100, 100],
            'low': [100, 100, 100, 100, 100],
            'close': [100, 100, 100, 100, 100]
        },
        "expected_true_ranges": [0.0, 0.0, 0.0, 0.0, 0.0],
        "expected_atr_period_3": {
            "final": 0.0
        }
    }
}

# SMA Test Cases - Hand-calculated reference values  
SMA_TEST_CASES = {
    "basic_average": {
        "description": "Simple increasing sequence for easy verification",
        "prices": [100, 102, 104, 106, 108, 110, 112, 114, 116, 118],
        "expected_sma_period_5": {
            "position_4": 104.0,  # (100+102+104+106+108)/5 = 104.0
            "position_9": 114.0   # (110+112+114+116+118)/5 = 114.0
        },
        "expected_sma_period_3": {
            "position_2": 102.0,  # (100+102+104)/3 = 102.0
            "position_9": 116.0   # (114+116+118)/3 = 116.0
        },
        "calculation_notes": [
            "SMA calculation: sum of n recent values divided by n",
            "First valid SMA appears at position (period-1)",
            "For period 5: first SMA at position 4 (0-indexed)",
            "For period 3: first SMA at position 2 (0-indexed)"
        ]
    },
    
    "constant_values": {
        "description": "Constant prices - SMA should equal the constant",
        "prices": [100, 100, 100, 100, 100, 100, 100, 100, 100, 100],
        "expected_sma_any_period": 100.0,
        "mathematical_property": "SMA of constant values should equal the constant"
    },
    
    "mathematical_properties": {
        "description": "Test cases for SMA mathematical properties",
        "monotonic_increasing": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
        "property_notes": [
            "SMA of monotonic increasing sequence should be monotonic increasing",
            "SMA should smooth out short-term variations",
            "Longer period SMAs should have less variation than shorter period SMAs"
        ]
    }
}

# Tolerance levels for trading applications
TOLERANCE_LEVELS = {
    'trading_standard': 1e-3,     # 0.1% - sufficient for trading decisions
    'strict_validation': 1e-4,    # 0.01% - for critical calculations like ATR
    'floating_point': 1e-10,      # For pure mathematical operations within pandas
}

# Mathematical validation notes
VALIDATION_NOTES = {
    "atr_algorithm": [
        "Uses Wilder's smoothing method for consistency with RSI",
        "True Range = max(H-L, |H-C_prev|, |L-C_prev|)",
        "First day TR = H-L (no previous close available)",
        "ATR = Exponentially Weighted Moving Average of TR with alpha=1/period"
    ],
    
    "sma_algorithm": [
        "Simple Moving Average = sum of n recent values / n", 
        "Rolling window calculation with min_periods=period",
        "Returns NaN for positions where insufficient data available",
        "Should be mathematically consistent with basic average calculation"
    ],
    
    "precision_expectations": [
        "Trading tolerance (0.1%) sufficient for position sizing decisions",
        "Strict tolerance (0.01%) for critical risk management calculations",
        "Floating-point precision limits apply to underlying pandas operations",
        "Focus on catching calculation errors that impact trading (>1% errors)"
    ]
}
