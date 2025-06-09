# ADR-002: Date Range Handling Convention

## Status
Accepted

## Context
The MEQSAP system handles date ranges for data fetching and backtesting. However, there has been confusion about whether `end_date` should be interpreted as inclusive or exclusive at different layers of the application, particularly when interfacing with yfinance which uses exclusive end dates.

## Decision

### User-Facing Convention
- **`end_date` in configuration is INCLUSIVE** - users specify the last calendar day they want data for
- Example: `end_date: 2022-12-31` means "include data for December 31, 2022"

### Internal Implementation
- `data.py` automatically adjusts for yfinance's exclusive behavior by adding 1 day when calling `yf.download()`
- Validation logic ensures data for the inclusive `end_date` is present, such as `dates.max() >= pd.Timestamp(end_date)` after yfinance fetching and adjustment.
- All other modules should treat the fetched data as containing data up to and including the configured end_date

### Documentation Requirements
- All user-facing documentation must explicitly state end_date inclusiveness
- Code comments must explain yfinance adjustments where they occur
- Test cases must verify inclusive behavior

## Consequences

### Positive
- Clear, unambiguous convention for users
- Consistent behavior across all modules
- Reduced cognitive load for developers

### Negative
- Requires careful implementation to maintain the adjustment layer
- Must be well-documented to prevent future confusion

## Compliance
- All date range handling must follow this ADR
- Violations of this convention are considered architectural degeneration
- Test coverage must verify inclusive end_date behavior
