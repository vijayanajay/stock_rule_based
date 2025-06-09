<!-- Status: Completed -->
# Story: Reporting and Presentation Layer Implementation

## Description
As the final component of the MEQSAP core pipeline, we need to implement the reporting and presentation layer that takes backtest results and presents them to users in a clear, actionable format. This module will generate a formatted "Executive Verdict" table in the terminal using the `rich` library and optionally create comprehensive PDF reports using `pyfolio` when the `--report` flag is used.

## Acceptance Criteria
1. Executive Verdict table displays key performance metrics in a formatted, readable terminal output
2. Vibe check results are clearly indicated with pass/fail status (✅/❌) in the verdict table
3. Robustness check results are presented with clear recommendations
4. PDF report generation works seamlessly with `pyfolio` when `--report` flag is used
5. Error handling provides clear, user-friendly messages for common issues
6. Terminal output is visually appealing and informative using `rich` library formatting
7. Report generation is optional and doesn't block the basic workflow
8. Module follows the modular monolith pattern and integrates cleanly with existing components
9. Unit tests cover all presentation logic and output formatting
10. Performance metrics are displayed with appropriate precision and units

## Implementation Details

### Reporting Module Architecture
Create `src/meqsap/reporting.py` as the presentation layer with the following components:

#### Executive Verdict Generator
- **Rich Table Formatting**: Use `rich.table.Table` to create visually appealing terminal output
- **Performance Metrics Display**: Show key metrics like total return, Sharpe ratio, max drawdown, etc.
- **Vibe Check Status**: Display pass/fail indicators for each validation check
- **Robustness Summary**: Present robustness check results with clear recommendations
- **Color Coding**: Use appropriate colors for positive/negative results and pass/fail status

#### PDF Report Generator
- **Pyfolio Integration**: Use `pyfolio.create_full_tear_sheet()` for comprehensive analysis
- **Portfolio Returns Preparation**: Convert backtest results to format expected by pyfolio
- **Report Customization**: Add MEQSAP branding and strategy configuration details
- **File Management**: Handle PDF generation, naming, and storage in appropriate directory

#### Data Formatting and Presentation
- **Metric Formatting**: Format numbers with appropriate precision (e.g., percentages, currency)
- **Date Formatting**: Present dates in user-friendly formats
- **Unit Handling**: Display metrics with proper units (%, $, days, etc.)
- **Conditional Formatting**: Highlight concerning metrics (high drawdown, low Sharpe, etc.)

### Core Functions

#### `generate_executive_verdict(backtest_result: BacktestResult, vibe_checks: VibeCheckResults, robustness_checks: RobustnessResults, strategy_config: StrategyConfig) -> None`
- Creates and displays the formatted Executive Verdict table in terminal
- Uses rich.console.Console for output
- Includes all key performance metrics and check results
- Provides clear pass/fail indicators for all validation checks

#### `generate_pdf_report(backtest_result: BacktestResult, strategy_config: StrategyConfig, output_path: str = None) -> str`
- Generates comprehensive PDF tear sheet using pyfolio
- Converts backtest results to pyfolio-compatible format
- Adds strategy configuration summary to report
- Returns path to generated PDF file
- Handles errors gracefully if pyfolio operations fail

#### `format_performance_metrics(backtest_result: BacktestResult) -> Dict[str, str]`
- Formats raw performance metrics for display
- Handles percentage formatting, decimal precision, and units
- Returns dictionary of formatted metric strings ready for presentation

#### `create_summary_table(strategy_config: StrategyConfig, backtest_result: BacktestResult) -> Table`
- Creates rich.Table with strategy summary information
- Includes ticker, date range, strategy parameters, and key metrics
- Returns formatted table ready for console output

### Data Models

#### `ReportConfig` (Pydantic Model)
```python
class ReportConfig(BaseModel):
    include_pdf: bool = False
    output_directory: str = "./reports"
    filename_prefix: str = "meqsap_report"
    include_plots: bool = True
    decimal_places: int = 4
```

#### `ExecutiveVerdictData` (Pydantic Model)
```python
class ExecutiveVerdictData(BaseModel):
    strategy_name: str
    ticker: str
    date_range: str
    total_return: str
    annual_return: str
    sharpe_ratio: str
    max_drawdown: str
    win_rate: str
    total_trades: int
    vibe_check_status: str
    robustness_score: str
    overall_verdict: str  # "PASS", "FAIL", "WARNING"
```

### Technical Implementation Requirements

#### Dependencies
- Add `rich`, `pyfolio`, `matplotlib` to requirements.txt
- Ensure compatibility with existing pandas/numpy versions
- Handle optional dependencies gracefully (pyfolio may have complex dependencies)

#### Rich Library Integration
- Use rich.console.Console for all terminal output
- Implement rich.table.Table for structured data presentation
- Use rich.text.Text for colored and styled text elements
- Implement rich.panel.Panel for grouped information display

#### Pyfolio Integration
- Convert vectorbt Portfolio results to pyfolio-compatible returns series
- Handle pyfolio's dependency requirements (matplotlib, seaborn, etc.)
- Manage PDF generation with proper error handling
- Customize tear sheet layout and content

#### Error Handling
- Graceful degradation when pyfolio dependencies are missing
- Clear error messages for file system issues (permissions, disk space)
- Validation of backtest results before presentation
- Fallback text output if rich library fails

#### File Management
- Create reports directory if it doesn't exist
- Generate unique filenames to avoid overwrites
- Clean up temporary files used in PDF generation
- Validate output paths and permissions

### CLI Integration Requirements

#### Command Line Arguments
- `--report`: Generate PDF report in addition to terminal output
- `--output-dir`: Specify custom directory for report generation
- `--no-color`: Disable colored terminal output for CI/CD environments
- `--quiet`: Suppress verbose terminal output, show only summary

#### Output Formatting
- Ensure terminal output works across different terminal sizes
- Handle wide tables gracefully on narrow terminals
- Provide clear separation between different sections of output
- Include timestamps and run information in output

### Testing Strategy

#### Unit Tests
- Test metric formatting functions with various input ranges
- Validate table creation and structure
- Test error handling for invalid inputs
- Mock pyfolio operations to test integration logic

#### Integration Tests
- Test complete reporting workflow with real backtest results
- Validate PDF generation end-to-end (if pyfolio available)
- Test terminal output formatting across different scenarios
- Verify file system operations and cleanup

#### Visual Tests
- Manual verification of terminal output appearance
- PDF report visual inspection checklist
- Cross-platform compatibility testing (Windows, macOS, Linux)

## Tasks Breakdown

### Module Setup and Foundation
- [ ] **Setup reporting module structure** - Create `src/meqsap/reporting.py` with basic module structure, imports, and logging setup
- [ ] **Define data models** - Implement `ReportConfig` and `ExecutiveVerdictData` Pydantic models with proper validation
- [ ] **Add dependencies** - Update `requirements.txt` with `rich`, `pyfolio`, `matplotlib`, and other required packages
- [ ] **Create module constants** - Define color schemes, formatting constants, and default configurations

### Data Formatting and Utilities
- [ ] **Implement metric formatting functions** - Create `format_performance_metrics()` with percentage, currency, and precision handling
- [ ] **Create date formatting utilities** - Implement functions for user-friendly date range and timestamp formatting
- [ ] **Build conditional formatting logic** - Create functions for color-coding metrics based on thresholds (good/bad performance)
- [ ] **Add unit handling utilities** - Implement proper unit display for percentages, currency, days, and counts

### Executive Verdict Table Generation
- [ ] **Create summary table builder** - Implement `create_summary_table()` using rich.Table for strategy overview
- [ ] **Build performance metrics table** - Create formatted table section for key performance indicators
- [ ] **Implement vibe check display** - Add section for vibe check results with ✅/❌ status indicators
- [ ] **Add robustness results section** - Create table section for robustness analysis with recommendations
- [ ] **Implement overall verdict logic** - Create algorithm to determine PASS/FAIL/WARNING status and display prominently
- [ ] **Complete executive verdict function** - Implement main `generate_executive_verdict()` function with all sections

### Rich Library Integration
- [ ] **Setup rich console configuration** - Initialize rich.Console with proper settings for terminal output
- [ ] **Implement table styling** - Create consistent styling for all tables including borders, colors, and alignment
- [ ] **Add panel and text formatting** - Implement rich.Panel for grouped information and rich.Text for styled elements
- [ ] **Create responsive layout handling** - Ensure tables adapt to different terminal widths gracefully
- [ ] **Add progress indicators** - Implement progress bars for long-running operations (PDF generation)

### PDF Report Generation
- [ ] **Implement data conversion for pyfolio** - Create functions to convert vectorbt results to pyfolio-compatible format
- [ ] **Setup pyfolio tear sheet generation** - Implement `generate_pdf_report()` with pyfolio.create_full_tear_sheet()
- [ ] **Add strategy metadata integration** - Include strategy configuration and MEQSAP branding in PDF reports
- [ ] **Implement file management** - Create unique filenames, directory creation, and path validation
- [ ] **Add PDF customization** - Customize tear sheet layout and add custom sections for MEQSAP-specific analysis

### Error Handling and Graceful Degradation
- [ ] **Implement dependency checking** - Add checks for optional dependencies (pyfolio, matplotlib) with graceful degradation
- [ ] **Create file system error handling** - Handle permissions, disk space, and path validation errors
- [ ] **Add data validation** - Validate backtest results before processing and provide clear error messages
- [ ] **Implement fallback mechanisms** - Create text-only output fallbacks when rich library fails
- [ ] **Add logging and debugging** - Implement comprehensive logging for troubleshooting report generation issues

### CLI Integration
- [ ] **Add command line argument parsing** - Implement `--report`, `--output-dir`, `--no-color`, and `--quiet` flags
- [ ] **Update main CLI module** - Integrate reporting functionality into existing CLI workflow
- [ ] **Implement output directory handling** - Add logic for custom report directories and default locations
- [ ] **Add terminal compatibility modes** - Handle different terminal capabilities and CI/CD environments
- [ ] **Create help documentation** - Add comprehensive help text for all reporting-related CLI options

### Testing and Quality Assurance
- [ ] **Create unit tests for formatting functions** - Test `tests/test_reporting.py` with various input ranges and edge cases
- [ ] **Implement table generation tests** - Test rich table creation and structure validation
- [ ] **Add PDF generation mocking tests** - Mock pyfolio operations to test integration logic without dependencies
- [ ] **Create integration tests** - Test complete reporting workflow with real backtest results
- [ ] **Add visual output verification** - Create manual testing checklist for terminal and PDF output appearance
- [ ] **Implement error handling tests** - Test all error conditions and graceful degradation scenarios
- [ ] **Add performance tests** - Ensure report generation completes within acceptable time limits
- [ ] **Create cross-platform compatibility tests** - Verify functionality on Windows, macOS, and Linux

### Documentation and Examples
- [ ] **Write module documentation** - Create comprehensive docstrings for all functions and classes
- [ ] **Add usage examples** - Create example scripts demonstrating reporting functionality
- [ ] **Update README** - Add reporting section to main project README with usage instructions
- [ ] **Create troubleshooting guide** - Document common issues and solutions for report generation
- [ ] **Add configuration examples** - Provide sample ReportConfig configurations for different use cases

### Integration and Finalization
- [ ] **Integrate with existing modules** - Ensure seamless integration with backtesting and validation modules
- [ ] **Perform end-to-end testing** - Test complete pipeline from data acquisition through report generation
- [ ] **Optimize performance** - Profile and optimize report generation for large datasets
- [ ] **Add configuration validation** - Validate all report configuration options and provide helpful error messages
- [ ] **Create deployment checklist** - Verify all dependencies and configurations for production deployment

## Definition of Done
- [ ] All acceptance criteria are met and tested
- [ ] Executive Verdict displays correctly in terminal with rich formatting
- [ ] PDF report generation works when pyfolio dependencies are available
- [ ] Graceful error handling for missing dependencies or file system issues
- [ ] Module passes all unit and integration tests
- [ ] Code follows project style guidelines and type hints
- [ ] Documentation is complete with usage examples
- [ ] Integration with existing CLI and backtest modules is seamless
- [ ] Performance is acceptable (sub-second for report generation)
- [ ] Cross-platform compatibility verified

## Dependencies
- **Prerequisite**: Story 01 (Project Setup and Configuration) - ✅ Completed
- **Prerequisite**: Story 02 (Data Acquisition and Caching) - ✅ Completed  
- **Prerequisite**: Story 03 (Signal Generation and Backtesting) - ✅ Completed
- **Successor**: Story 05 (CLI Integration and Error Handling Enhancement)

## Detailed Pseudocode

### Executive Verdict Generation Function

**Component:** `Reporting Module`
**Function:** `generate_executive_verdict`

**Inputs:**
* `BacktestResult` object containing all performance metrics
* `VibeCheckResults` object with validation check outcomes
* `RobustnessResults` object with robustness analysis
* `StrategyConfig` object with strategy parameters

**Output:**
* Formatted terminal output using rich library displaying comprehensive analysis verdict

**Steps:**
1. **Create Main Verdict Table**
   * Initialize rich Table with appropriate styling
   * Add columns for metric names, values, and status indicators
   * Set table title with strategy name and analysis date

2. **Format and Add Performance Metrics**
   * Format total return as percentage with appropriate color coding
   * Format Sharpe ratio with conditional formatting (good/bad thresholds)
   * Format max drawdown with warning colors for high values
   * Add win rate, total trades, and other key metrics

3. **Add Vibe Check Results**
   * Display each vibe check with ✅/❌ status indicators
   * Include explanatory messages for any failed checks
   * Summarize overall vibe check status

4. **Add Robustness Check Results**
   * Display robustness score with color coding
   * Show high-fees impact analysis
   * Include turnover rate assessment
   * Add recommendations based on results

5. **Generate Overall Verdict**
   * Determine overall PASS/FAIL/WARNING status
   * Display prominent verdict with appropriate styling
   * Include key recommendations for strategy improvement

6. **Display to Console**
   * Use rich Console to render the complete table
   * Add decorative panels for important information
   * Ensure proper formatting across different terminal sizes

### PDF Report Generation Function

**Component:** `Reporting Module`  
**Function:** `generate_pdf_report`

**Inputs:**
* `BacktestResult` object with portfolio performance data
* `StrategyConfig` object with strategy parameters
* Optional output path for PDF file

**Output:**
* Path to generated PDF report file
* Raises exceptions for generation failures

**Steps:**
1. **Prepare Data for Pyfolio**
   * Convert vectorbt portfolio results to pandas Series of returns
   * Ensure proper date indexing and return calculation
   * Handle any data format inconsistencies

2. **Configure Report Generation**
   * Set up matplotlib backend for PDF output
   * Configure pyfolio parameters for tear sheet generation
   * Prepare strategy metadata for inclusion in report

3. **Generate Tear Sheet**
   * Call pyfolio.create_full_tear_sheet() with prepared data
   * Include strategy configuration summary as custom section
   * Add MEQSAP branding and metadata

4. **Handle File Operations**
   * Generate unique filename based on strategy and timestamp
   * Ensure output directory exists, create if necessary
   * Save PDF to specified or default location

5. **Cleanup and Validation**
   * Verify PDF file was created successfully
   * Clean up any temporary matplotlib files
   * Return path to generated report for user reference

### Performance Metrics Formatting Function

**Component:** `Reporting Module`
**Function:** `format_performance_metrics`

**Inputs:**
* `BacktestResult` object containing raw performance statistics

**Output:**
* Dictionary of formatted metric strings ready for display

**Steps:**
1. **Extract Raw Metrics**
   * Retrieve total return, annual return, Sharpe ratio from backtest results
   * Extract maximum drawdown, win rate, and trade count
   * Get volatility and other risk metrics

2. **Apply Percentage Formatting**
   * Convert decimal returns to percentage format with appropriate precision
   * Format drawdown as negative percentage with warning styling
   * Format win rate as percentage with conditional color coding

3. **Apply Currency and Ratio Formatting**
   * Format dollar amounts with proper currency symbols and commas
   * Format Sharpe ratio with 2-3 decimal places for readability
   * Format volatility as annualized percentage

4. **Add Conditional Color Codes**
   * Apply green color codes for positive returns and high Sharpe ratios
   * Apply red color codes for high drawdowns and low performance
   * Apply yellow/amber for moderate performance metrics

5. **Return Formatted Dictionary**
   * Assemble all formatted strings into labeled dictionary
   * Include rich markup for color and styling information
   * Ensure consistent formatting across all metric types

### Summary Table Creation Function

**Component:** `Reporting Module`
**Function:** `create_summary_table`

**Inputs:**
* `StrategyConfig` object with strategy parameters
* `BacktestResult` object with performance data

**Output:**
* Rich Table object formatted for console display

**Steps:**
1. **Initialize Table Structure**
   * Create rich Table with appropriate column headers
   * Set table styling with borders and title
   * Configure column alignment and width settings

2. **Add Strategy Information**
   * Add row for ticker symbol and market information
   * Add row for date range with formatted start and end dates
   * Add row for strategy type and key parameters

3. **Add Performance Summary**
   * Add row for total return with color-coded formatting
   * Add row for annualized return and volatility
   * Add row for Sharpe ratio and maximum drawdown

4. **Add Trade Statistics**
   * Add row for total number of trades executed
   * Add row for win rate and average trade duration
   * Add row for turnover rate and trading frequency

5. **Apply Final Styling**
   * Set appropriate row colors based on performance thresholds
   * Add emphasis to key metrics using bold or highlighting
   * Ensure table width fits standard terminal dimensions

### Verdict Determination Function

**Component:** `Reporting Module`
**Function:** `determine_overall_verdict`

**Inputs:**
* `VibeCheckResults` object with validation outcomes
* `RobustnessResults` object with robustness analysis
* `BacktestResult` object with performance metrics

**Output:**
* Overall verdict string: "PASS", "FAIL", or "WARNING"
* List of recommendation strings for strategy improvement

**Steps:**
1. **Evaluate Vibe Check Status**
   * Check if minimum trade count requirement is met
   * Verify turnover rate is within acceptable bounds
   * Assess if any critical vibe checks have failed

2. **Evaluate Performance Thresholds**
   * Check if Sharpe ratio meets minimum threshold (typically > 1.0)
   * Verify maximum drawdown is within acceptable limits (< 20%)
   * Assess if total return justifies the risk taken

3. **Evaluate Robustness Results**
   * Check robustness score against minimum acceptable level
   * Assess impact of higher transaction costs on performance
   * Verify strategy stability across different market conditions

4. **Determine Overall Status**
   * Return "FAIL" if any critical checks fail or performance is poor
   * Return "WARNING" if performance is marginal or robustness is questionable
   * Return "PASS" only if all checks pass and performance is strong

5. **Generate Recommendations**
   * Create specific recommendations based on failed or marginal checks
   * Suggest parameter adjustments for improving robustness
   * Provide guidance on risk management and position sizing
