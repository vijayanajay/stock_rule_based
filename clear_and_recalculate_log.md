# Clear and Recalculate Log

**Command:** `python run.py clear-and-recalculate --force`
**Date:** 2025-07-09 01:46:37
**Database:** data\kiss_signal.db

## Console Output

```
[01:46:11] INFO     === KISS Signal CLI Run Started ===                                                                
Clearing all strategies from database...
✅ Deleted 0 strategy records from database
Starting fresh backtesting run...
[01:46:12] INFO     Loaded 92 symbols from universe                                                                    
           INFO     Backtester initialized: hold_period=20, min_trades=10                                              
           WARNING  Could not infer frequency for RELIANCE. Forcing daily frequency ('D').                             
           INFO     Backtesting 4 rule combinations for RELIANCE                                                       
           INFO     Rule 'engulfing_pattern' generated 20 signals on 1095 data points                                  
           INFO     Rule 'sma_cross_under' generated 29 signals on 1095 data points                                    
[01:46:23] INFO     Rule 'engulfing_pattern' generated 20 signals on 1095 data points                                  
           INFO     Rule 'rsi_oversold' generated 848 signals on 1095 data points                                      
           INFO     Rule 'sma_cross_under' generated 29 signals on 1095 data points                                    
           INFO     Rule 'engulfing_pattern' generated 20 signals on 1095 data points                                  
           INFO     Rule 'volume_spike' generated 46 signals on 1095 data points                                       
           INFO     Rule 'sma_cross_under' generated 29 signals on 1095 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'RELIANCE' generated only 2    
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 20 signals on 1095 data points                                  
           INFO     Rule 'price_above_sma' generated 581 signals on 1095 data points                                   
           INFO     Rule 'sma_cross_under' generated 29 signals on 1095 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_uptrend_context' on 'RELIANCE' generated only 9 
                    trades, which is below the threshold of 10.                                                        
           INFO     find_optimal_strategies completed in 11.76s                                                        
           WARNING  Could not infer frequency for INFY. Forcing daily frequency ('D').                                 
           INFO     Backtesting 4 rule combinations for INFY                                                           
           INFO     Rule 'engulfing_pattern' generated 15 signals on 1095 data points                                  
           INFO     Rule 'sma_cross_under' generated 28 signals on 1095 data points                                    
           INFO     Rule 'engulfing_pattern' generated 15 signals on 1095 data points                                  
           INFO     Rule 'rsi_oversold' generated 822 signals on 1095 data points                                      
           INFO     Rule 'sma_cross_under' generated 28 signals on 1095 data points                                    
           INFO     Rule 'engulfing_pattern' generated 15 signals on 1095 data points                                  
           INFO     Rule 'volume_spike' generated 60 signals on 1095 data points                                       
           INFO     Rule 'sma_cross_under' generated 28 signals on 1095 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'INFY' generated only 2 trades,
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 15 signals on 1095 data points                                  
           INFO     Rule 'price_above_sma' generated 597 signals on 1095 data points                                   
           INFO     Rule 'sma_cross_under' generated 28 signals on 1095 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_uptrend_context' on 'INFY' generated only 6     
                    trades, which is below the threshold of 10.                                                        
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for TCS. Forcing daily frequency ('D').                                  
           INFO     Backtesting 4 rule combinations for TCS                                                            
           INFO     Rule 'engulfing_pattern' generated 30 signals on 1095 data points                                  
           INFO     Rule 'sma_cross_under' generated 28 signals on 1095 data points                                    
           INFO     Rule 'engulfing_pattern' generated 30 signals on 1095 data points                                  
[01:46:24] INFO     Rule 'rsi_oversold' generated 824 signals on 1095 data points                                      
           INFO     Rule 'sma_cross_under' generated 28 signals on 1095 data points                                    
           INFO     Rule 'engulfing_pattern' generated 30 signals on 1095 data points                                  
           INFO     Rule 'volume_spike' generated 57 signals on 1095 data points                                       
           INFO     Rule 'sma_cross_under' generated 28 signals on 1095 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'TCS' generated only 2 trades, 
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 30 signals on 1095 data points                                  
           INFO     Rule 'price_above_sma' generated 582 signals on 1095 data points                                   
           INFO     Rule 'sma_cross_under' generated 28 signals on 1095 data points                                    
           INFO     find_optimal_strategies completed in 0.16s                                                         
           WARNING  Could not infer frequency for HDFCBANK. Forcing daily frequency ('D').                             
           INFO     Backtesting 4 rule combinations for HDFCBANK                                                       
           INFO     Rule 'engulfing_pattern' generated 36 signals on 1095 data points                                  
           INFO     Rule 'sma_cross_under' generated 36 signals on 1095 data points                                    
           INFO     Rule 'engulfing_pattern' generated 36 signals on 1095 data points                                  
           INFO     Rule 'rsi_oversold' generated 906 signals on 1095 data points                                      
           INFO     Rule 'sma_cross_under' generated 36 signals on 1095 data points                                    
           INFO     Rule 'engulfing_pattern' generated 36 signals on 1095 data points                                  
           INFO     Rule 'volume_spike' generated 51 signals on 1095 data points                                       
           INFO     Rule 'sma_cross_under' generated 36 signals on 1095 data points                                    
           WARNING  Low win rate detected for HDFCBANK: 0.0% with 2 trades                                             
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_volume_spike                            
           WARNING  Average PnL: -3722.08, Sharpe: -0.69                                                               
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'HDFCBANK' generated only 2    
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 36 signals on 1095 data points                                  
           INFO     Rule 'price_above_sma' generated 617 signals on 1095 data points                                   
           INFO     Rule 'sma_cross_under' generated 36 signals on 1095 data points                                    
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for ICICIBANK. Forcing daily frequency ('D').                            
           INFO     Backtesting 4 rule combinations for ICICIBANK                                                      
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1095 data points                                  
           INFO     Rule 'sma_cross_under' generated 28 signals on 1095 data points                                    
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1095 data points                                  
           INFO     Rule 'rsi_oversold' generated 938 signals on 1095 data points                                      
           INFO     Rule 'sma_cross_under' generated 28 signals on 1095 data points                                    
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1095 data points                                  
           INFO     Rule 'volume_spike' generated 45 signals on 1095 data points                                       
           INFO     Rule 'sma_cross_under' generated 28 signals on 1095 data points                                    
           WARNING  Low win rate detected for ICICIBANK: 0.0% with 2 trades                                            
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_volume_spike                            
           WARNING  Average PnL: -1077.38, Sharpe: -0.34                                                               
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'ICICIBANK' generated only 2   
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1095 data points                                  
           INFO     Rule 'price_above_sma' generated 647 signals on 1095 data points                                   
           INFO     Rule 'sma_cross_under' generated 28 signals on 1095 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for SBIN. Forcing daily frequency ('D').                                 
           INFO     Backtesting 4 rule combinations for SBIN                                                           
           INFO     Rule 'engulfing_pattern' generated 16 signals on 1095 data points                                  
           INFO     Rule 'sma_cross_under' generated 30 signals on 1095 data points                                    
           INFO     Rule 'engulfing_pattern' generated 16 signals on 1095 data points                                  
           INFO     Rule 'rsi_oversold' generated 896 signals on 1095 data points                                      
           INFO     Rule 'sma_cross_under' generated 30 signals on 1095 data points                                    
           INFO     Rule 'engulfing_pattern' generated 16 signals on 1095 data points                                  
           INFO     Rule 'volume_spike' generated 58 signals on 1095 data points                                       
           INFO     Rule 'sma_cross_under' generated 30 signals on 1095 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'SBIN' generated only 2 trades,
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 16 signals on 1095 data points                                  
           INFO     Rule 'price_above_sma' generated 627 signals on 1095 data points                                   
           INFO     Rule 'sma_cross_under' generated 30 signals on 1095 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for WIPRO. Forcing daily frequency ('D').                                
           INFO     Backtesting 4 rule combinations for WIPRO                                                          
           INFO     Rule 'engulfing_pattern' generated 21 signals on 1095 data points                                  
           INFO     Rule 'sma_cross_under' generated 29 signals on 1095 data points                                    
           INFO     Rule 'engulfing_pattern' generated 21 signals on 1095 data points                                  
           INFO     Rule 'rsi_oversold' generated 815 signals on 1095 data points                                      
           INFO     Rule 'sma_cross_under' generated 29 signals on 1095 data points                                    
           INFO     Rule 'engulfing_pattern' generated 21 signals on 1095 data points                                  
           INFO     Rule 'volume_spike' generated 65 signals on 1095 data points                                       
           INFO     Rule 'sma_cross_under' generated 29 signals on 1095 data points                                    
[01:46:25] WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'WIPRO' generated only 1       
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 21 signals on 1095 data points                                  
           INFO     Rule 'price_above_sma' generated 604 signals on 1095 data points                                   
           INFO     Rule 'sma_cross_under' generated 29 signals on 1095 data points                                    
           INFO     find_optimal_strategies completed in 0.53s                                                         
           WARNING  Could not infer frequency for HCLTECH. Forcing daily frequency ('D').                              
           INFO     Backtesting 4 rule combinations for HCLTECH                                                        
           INFO     Rule 'engulfing_pattern' generated 37 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 37 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 887 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 37 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 57 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'HCLTECH' generated only 3     
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 37 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 680 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for TECHM. Forcing daily frequency ('D').                                
           INFO     Backtesting 4 rule combinations for TECHM                                                          
           INFO     Rule 'engulfing_pattern' generated 15 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 15 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 900 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 15 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 71 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'TECHM' generated only 0       
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 15 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 599 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.11s                                                         
           WARNING  Could not infer frequency for LTIM. Forcing daily frequency ('D').                                 
           INFO     Backtesting 4 rule combinations for LTIM                                                           
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1094 data points                                  
           INFO     Rule 'sma_cross_under' generated 28 signals on 1094 data points                                    
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1094 data points                                  
           INFO     Rule 'rsi_oversold' generated 827 signals on 1094 data points                                      
           INFO     Rule 'sma_cross_under' generated 28 signals on 1094 data points                                    
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1094 data points                                  
           INFO     Rule 'volume_spike' generated 78 signals on 1094 data points                                       
           INFO     Rule 'sma_cross_under' generated 28 signals on 1094 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'LTIM' generated only 4 trades,
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1094 data points                                  
           INFO     Rule 'price_above_sma' generated 594 signals on 1094 data points                                   
           INFO     Rule 'sma_cross_under' generated 28 signals on 1094 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for BHARTIARTL. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for BHARTIARTL                                                     
           INFO     Rule 'engulfing_pattern' generated 34 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 34 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 1010 signals on 1093 data points                                     
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 34 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 63 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'BHARTIARTL' generated only 5  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 34 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 725 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.11s                                                         
           WARNING  Could not infer frequency for KOTAKBANK. Forcing daily frequency ('D').                            
           INFO     Backtesting 4 rule combinations for KOTAKBANK                                                      
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 863 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 55 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           WARNING  Low win rate detected for KOTAKBANK: 0.0% with 1 trades                                            
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_volume_spike                            
           WARNING  Average PnL: -103.24, Sharpe: 0.01                                                                 
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'KOTAKBANK' generated only 1   
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 584 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for AXISBANK. Forcing daily frequency ('D').                             
           INFO     Backtesting 4 rule combinations for AXISBANK                                                       
           INFO     Rule 'engulfing_pattern' generated 30 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 30 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 920 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 30 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 66 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'AXISBANK' generated only 4    
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 30 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 595 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for INDUSINDBK. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for INDUSINDBK                                                     
           INFO     Rule 'engulfing_pattern' generated 26 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 26 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 841 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 26 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 72 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'INDUSINDBK' generated only 5  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 26 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 598 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for BAJFINANCE. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for BAJFINANCE                                                     
           INFO     Rule 'engulfing_pattern' generated 31 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 31 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 836 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 31 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 81 signals on 1093 data points                                       
[01:46:26] INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'BAJFINANCE' generated only 4  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 31 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 543 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.14s                                                         
           WARNING  Could not infer frequency for BAJAJFINSV. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for BAJAJFINSV                                                     
           INFO     Rule 'engulfing_pattern' generated 31 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 26 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 31 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 875 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 26 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 31 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 70 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 26 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'BAJAJFINSV' generated only 4  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 31 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 601 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 26 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.22s                                                         
           WARNING  Could not infer frequency for MARUTI. Forcing daily frequency ('D').                               
           INFO     Backtesting 4 rule combinations for MARUTI                                                         
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 32 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 882 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 32 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 56 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 32 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'MARUTI' generated only 2      
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 580 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 32 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.14s                                                         
           WARNING  Could not infer frequency for TATAMOTORS. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for TATAMOTORS                                                     
           INFO     Rule 'engulfing_pattern' generated 19 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 23 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 19 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 857 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 23 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 19 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 64 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 23 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'TATAMOTORS' generated only 3  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 19 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 576 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 23 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_uptrend_context' on 'TATAMOTORS' generated only 
                    9 trades, which is below the threshold of 10.                                                      
           INFO     find_optimal_strategies completed in 0.14s                                                         
           WARNING  Could not infer frequency for M&M. Forcing daily frequency ('D').                                  
           INFO     Backtesting 4 rule combinations for M&M                                                            
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 33 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 934 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 33 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 58 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 33 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'M&M' generated only 0 trades, 
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 675 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 33 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for HEROMOTOCO. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for HEROMOTOCO                                                     
           INFO     Rule 'engulfing_pattern' generated 19 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 26 signals on 1093 data points                                    
           WARNING  Low win rate detected for HEROMOTOCO: 18.8% with 16 trades                                         
           WARNING  Rule combination: bullish_engulfing_reversal                                                       
           WARNING  Average PnL: -1255.92, Sharpe: -0.70                                                               
           INFO     Rule 'engulfing_pattern' generated 19 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 838 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 26 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 19 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 94 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 26 signals on 1093 data points                                    
           WARNING  Low win rate detected for HEROMOTOCO: 0.0% with 2 trades                                           
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_volume_spike                            
           WARNING  Average PnL: -5719.74, Sharpe: -1.24                                                               
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'HEROMOTOCO' generated only 2  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 19 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 571 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 26 signals on 1093 data points                                    
           WARNING  Low win rate detected for HEROMOTOCO: 18.2% with 11 trades                                         
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_uptrend_context                         
           WARNING  Average PnL: -1138.12, Sharpe: -0.52                                                               
           INFO     find_optimal_strategies completed in 0.15s                                                         
           WARNING  Could not infer frequency for BAJAJ-AUTO. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for BAJAJ-AUTO                                                     
           INFO     Rule 'engulfing_pattern' generated 26 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 25 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 26 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 899 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 25 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 26 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 66 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 25 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'BAJAJ-AUTO' generated only 4  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 26 signals on 1093 data points                                  
[01:46:27] INFO     Rule 'price_above_sma' generated 651 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 25 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for EICHERMOT. Forcing daily frequency ('D').                            
           INFO     Backtesting 4 rule combinations for EICHERMOT                                                      
           INFO     Rule 'engulfing_pattern' generated 35 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 35 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 921 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 35 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 66 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'EICHERMOT' generated only 2   
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 35 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 649 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.19s                                                         
           WARNING  Could not infer frequency for ASIANPAINT. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for ASIANPAINT                                                     
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 782 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 72 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           WARNING  Low win rate detected for ASIANPAINT: 0.0% with 3 trades                                           
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_volume_spike                            
           WARNING  Average PnL: -2646.49, Sharpe: -0.60                                                               
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'ASIANPAINT' generated only 3  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 532 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           WARNING  Low win rate detected for ASIANPAINT: 18.2% with 11 trades                                         
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_uptrend_context                         
           WARNING  Average PnL: -1666.80, Sharpe: -0.84                                                               
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for NESTLEIND. Forcing daily frequency ('D').                            
           INFO     Backtesting 4 rule combinations for NESTLEIND                                                      
           INFO     Rule 'engulfing_pattern' generated 29 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 36 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 29 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 889 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 36 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 29 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 55 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 36 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'NESTLEIND' generated only 3   
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 29 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 578 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 36 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for HINDUNILVR. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for HINDUNILVR                                                     
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 34 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 803 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 34 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 54 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 34 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'HINDUNILVR' generated only 0  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 510 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 34 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.11s                                                         
           WARNING  Could not infer frequency for ITC. Forcing daily frequency ('D').                                  
           INFO     Backtesting 4 rule combinations for ITC                                                            
           INFO     Rule 'engulfing_pattern' generated 21 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 21 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 895 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 21 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 55 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'ITC' generated only 2 trades, 
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 21 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 627 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for BRITANNIA. Forcing daily frequency ('D').                            
           INFO     Backtesting 4 rule combinations for BRITANNIA                                                      
           INFO     Rule 'engulfing_pattern' generated 36 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 36 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 881 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 36 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 64 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'BRITANNIA' generated only 6   
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 36 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 614 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for DABUR. Forcing daily frequency ('D').                                
           INFO     Backtesting 4 rule combinations for DABUR                                                          
           INFO     Rule 'engulfing_pattern' generated 35 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 26 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 35 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 838 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 26 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 35 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 64 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 26 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'DABUR' generated only 2       
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 35 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 532 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 26 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.11s                                                         
           WARNING  Could not infer frequency for GODREJCP. Forcing daily frequency ('D').                             
           INFO     Backtesting 4 rule combinations for GODREJCP                                                       
           INFO     Rule 'engulfing_pattern' generated 22 signals on 1093 data points                                  
[01:46:28] INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 22 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 893 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 22 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 73 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'GODREJCP' generated only 2    
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 22 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 581 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for ULTRACEMCO. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for ULTRACEMCO                                                     
           INFO     Rule 'engulfing_pattern' generated 26 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 26 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 954 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 26 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 61 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'ULTRACEMCO' generated only 3  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 26 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 630 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.14s                                                         
           WARNING  Could not infer frequency for JSWSTEEL. Forcing daily frequency ('D').                             
           INFO     Backtesting 4 rule combinations for JSWSTEEL                                                       
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 33 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 915 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 33 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 52 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 33 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'JSWSTEEL' generated only 3    
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 655 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 33 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.34s                                                         
           WARNING  Could not infer frequency for TATASTEEL. Forcing daily frequency ('D').                            
           INFO     Backtesting 4 rule combinations for TATASTEEL                                                      
           INFO     Rule 'engulfing_pattern' generated 12 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 12 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 912 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 12 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 63 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'TATASTEEL' generated only 1   
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 12 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 615 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_uptrend_context' on 'TATASTEEL' generated only 6
                    trades, which is below the threshold of 10.                                                        
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for HINDALCO. Forcing daily frequency ('D').                             
           INFO     Backtesting 4 rule combinations for HINDALCO                                                       
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 899 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 71 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'HINDALCO' generated only 1    
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 659 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for VEDL. Forcing daily frequency ('D').                                 
           INFO     Backtesting 4 rule combinations for VEDL                                                           
           INFO     Rule 'engulfing_pattern' generated 12 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 12 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 945 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 12 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 91 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           WARNING  Low win rate detected for VEDL: 0.0% with 2 trades                                                 
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_volume_spike                            
           WARNING  Average PnL: -5524.76, Sharpe: -0.88                                                               
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'VEDL' generated only 2 trades,
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 12 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 634 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
[01:46:29] WARNING  Strategy 'bullish_engulfing_reversal + filter_with_uptrend_context' on 'VEDL' generated only 8     
                    trades, which is below the threshold of 10.                                                        
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for COALINDIA. Forcing daily frequency ('D').                            
           INFO     Backtesting 4 rule combinations for COALINDIA                                                      
           INFO     Rule 'engulfing_pattern' generated 13 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 13 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 914 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 13 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 69 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           WARNING  Low win rate detected for COALINDIA: 0.0% with 2 trades                                            
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_volume_spike                            
           WARNING  Average PnL: -4244.06, Sharpe: -0.90                                                               
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'COALINDIA' generated only 2   
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 13 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 632 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_uptrend_context' on 'COALINDIA' generated only 7
                    trades, which is below the threshold of 10.                                                        
           INFO     find_optimal_strategies completed in 0.15s                                                         
           WARNING  Could not infer frequency for NTPC. Forcing daily frequency ('D').                                 
           INFO     Backtesting 4 rule combinations for NTPC                                                           
           INFO     Rule 'engulfing_pattern' generated 20 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 20 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 963 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 20 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 81 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'NTPC' generated only 3 trades,
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 20 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 665 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for POWERGRID. Forcing daily frequency ('D').                            
           INFO     Backtesting 4 rule combinations for POWERGRID                                                      
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 25 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 946 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 25 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 71 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 25 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'POWERGRID' generated only 5   
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 649 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 25 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for ONGC. Forcing daily frequency ('D').                                 
           INFO     Backtesting 4 rule combinations for ONGC                                                           
           INFO     Rule 'engulfing_pattern' generated 16 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 16 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 930 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 16 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 65 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'ONGC' generated only 0 trades,
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 16 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 679 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.15s                                                         
           WARNING  Could not infer frequency for IOC. Forcing daily frequency ('D').                                  
           INFO     Backtesting 4 rule combinations for IOC                                                            
           INFO     Rule 'engulfing_pattern' generated 17 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 25 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 17 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 915 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 25 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 17 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 69 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 25 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'IOC' generated only 1 trades, 
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 17 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 622 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 25 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for BPCL. Forcing daily frequency ('D').                                 
           INFO     Backtesting 4 rule combinations for BPCL                                                           
           INFO     Rule 'engulfing_pattern' generated 24 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 24 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 895 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 24 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 81 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'BPCL' generated only 2 trades,
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 24 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 585 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for GRASIM. Forcing daily frequency ('D').                               
           INFO     Backtesting 4 rule combinations for GRASIM                                                         
           INFO     Rule 'engulfing_pattern' generated 32 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 32 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 32 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 944 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 32 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 32 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 69 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 32 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'GRASIM' generated only 5      
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 32 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 638 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 32 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for ADANIPORTS. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for ADANIPORTS                                                     
           INFO     Rule 'engulfing_pattern' generated 15 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
[01:46:30] INFO     Rule 'engulfing_pattern' generated 15 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 913 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 15 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 91 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'ADANIPORTS' generated only 2  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 15 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 609 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_uptrend_context' on 'ADANIPORTS' generated only 
                    9 trades, which is below the threshold of 10.                                                      
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for LTTS. Forcing daily frequency ('D').                                 
           INFO     Backtesting 4 rule combinations for LTTS                                                           
           INFO     Rule 'engulfing_pattern' generated 25 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 25 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 863 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 25 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 90 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'LTTS' generated only 4 trades,
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 25 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 618 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for MPHASIS. Forcing daily frequency ('D').                              
           INFO     Backtesting 4 rule combinations for MPHASIS                                                        
           INFO     Rule 'engulfing_pattern' generated 19 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 19 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 832 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 19 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 78 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'MPHASIS' generated only 2     
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 19 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 615 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for PERSISTENT. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for PERSISTENT                                                     
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 26 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 924 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 26 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 81 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 26 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'PERSISTENT' generated only 2  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 649 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 26 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for ETERNAL. Forcing daily frequency ('D').                              
           INFO     Backtesting 4 rule combinations for ETERNAL                                                        
           INFO     Rule 'engulfing_pattern' generated 1 signals on 89 data points                                     
           INFO     Rule 'sma_cross_under' generated 3 signals on 89 data points                                       
           WARNING  Low win rate detected for ETERNAL: 0.0% with 1 trades                                              
           WARNING  Rule combination: bullish_engulfing_reversal                                                       
           WARNING  Average PnL: -1750.05, Sharpe: -0.94                                                               
           WARNING  Strategy 'bullish_engulfing_reversal' on 'ETERNAL' generated only 1 trades, which is below the     
                    threshold of 10.                                                                                   
           INFO     Rule 'engulfing_pattern' generated 1 signals on 89 data points                                     
           INFO     Rule 'rsi_oversold' generated 88 signals on 89 data points                                         
           INFO     Rule 'sma_cross_under' generated 3 signals on 89 data points                                       
           WARNING  Low win rate detected for ETERNAL: 0.0% with 1 trades                                              
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_rsi_oversold                            
           WARNING  Average PnL: -1750.05, Sharpe: -0.94                                                               
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_rsi_oversold' on 'ETERNAL' generated only 1     
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 1 signals on 89 data points                                     
           INFO     Rule 'volume_spike' generated 3 signals on 89 data points                                          
           INFO     Rule 'sma_cross_under' generated 3 signals on 89 data points                                       
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'ETERNAL' generated only 0     
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 1 signals on 89 data points                                     
           INFO     Rule 'price_above_sma' generated 54 signals on 89 data points                                      
           INFO     Rule 'sma_cross_under' generated 3 signals on 89 data points                                       
           WARNING  Low win rate detected for ETERNAL: 0.0% with 1 trades                                              
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_uptrend_context                         
           WARNING  Average PnL: -1750.05, Sharpe: -0.94                                                               
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_uptrend_context' on 'ETERNAL' generated only 1  
                    trades, which is below the threshold of 10.                                                        
           INFO     find_optimal_strategies completed in 0.15s                                                         
           WARNING  Could not infer frequency for SUNPHARMA. Forcing daily frequency ('D').                            
           INFO     Backtesting 4 rule combinations for SUNPHARMA                                                      
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 22 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 909 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 22 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 61 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 22 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'SUNPHARMA' generated only 3   
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 646 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 22 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.18s                                                         
           WARNING  Could not infer frequency for DRREDDY. Forcing daily frequency ('D').                              
           INFO     Backtesting 4 rule combinations for DRREDDY                                                        
           INFO     Rule 'engulfing_pattern' generated 19 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 19 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 850 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 19 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 62 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'DRREDDY' generated only 3     
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 19 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 603 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for CIPLA. Forcing daily frequency ('D').                                
           INFO     Backtesting 4 rule combinations for CIPLA                                                          
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
[01:46:31] INFO     Rule 'engulfing_pattern' generated 28 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 909 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 61 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'CIPLA' generated only 3       
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 635 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for DIVISLAB. Forcing daily frequency ('D').                             
           INFO     Backtesting 4 rule combinations for DIVISLAB                                                       
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 916 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 77 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'DIVISLAB' generated only 8    
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 619 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for APOLLOHOSP. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for APOLLOHOSP                                                     
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 899 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 55 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Low win rate detected for APOLLOHOSP: 0.0% with 1 trades                                           
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_volume_spike                            
           WARNING  Average PnL: -1813.28, Sharpe: -0.22                                                               
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'APOLLOHOSP' generated only 1  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 620 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for LICI. Forcing daily frequency ('D').                                 
           INFO     Backtesting 4 rule combinations for LICI                                                           
           INFO     Rule 'engulfing_pattern' generated 9 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal' on 'LICI' generated only 9 trades, which is below the        
                    threshold of 10.                                                                                   
           INFO     Rule 'engulfing_pattern' generated 9 signals on 1093 data points                                   
           INFO     Rule 'rsi_oversold' generated 796 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_rsi_oversold' on 'LICI' generated only 8 trades,
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 9 signals on 1093 data points                                   
           INFO     Rule 'volume_spike' generated 77 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           WARNING  Low win rate detected for LICI: 0.0% with 2 trades                                                 
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_volume_spike                            
           WARNING  Average PnL: -3729.52, Sharpe: -0.73                                                               
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'LICI' generated only 2 trades,
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 9 signals on 1093 data points                                   
           INFO     Rule 'price_above_sma' generated 523 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           WARNING  Low win rate detected for LICI: 16.7% with 6 trades                                                
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_uptrend_context                         
           WARNING  Average PnL: -1333.55, Sharpe: -0.35                                                               
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_uptrend_context' on 'LICI' generated only 6     
                    trades, which is below the threshold of 10.                                                        
           INFO     find_optimal_strategies completed in 0.14s                                                         
           WARNING  Could not infer frequency for SBILIFE. Forcing daily frequency ('D').                              
           INFO     Backtesting 4 rule combinations for SBILIFE                                                        
           INFO     Rule 'engulfing_pattern' generated 34 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 34 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 879 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 34 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 72 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'SBILIFE' generated only 4     
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 34 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 593 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for HDFCLIFE. Forcing daily frequency ('D').                             
           INFO     Backtesting 4 rule combinations for HDFCLIFE                                                       
           INFO     Rule 'engulfing_pattern' generated 25 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 25 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 869 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 25 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 76 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'HDFCLIFE' generated only 5    
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 25 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 583 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.15s                                                         
           WARNING  Could not infer frequency for ICICIPRULI. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for ICICIPRULI                                                     
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 790 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 87 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'ICICIPRULI' generated only 5  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 541 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for BAJAJHLDNG. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for BAJAJHLDNG                                                     
           INFO     Rule 'engulfing_pattern' generated 21 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
[01:46:32] INFO     Rule 'engulfing_pattern' generated 21 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 956 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 21 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 90 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'BAJAJHLDNG' generated only 5  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 21 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 626 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.17s                                                         
           WARNING  Could not infer frequency for SHREECEM. Forcing daily frequency ('D').                             
           INFO     Backtesting 4 rule combinations for SHREECEM                                                       
           INFO     Rule 'engulfing_pattern' generated 29 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 34 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 29 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 866 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 34 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 29 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 70 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 34 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'SHREECEM' generated only 0    
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 29 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 588 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 34 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for JKCEMENT. Forcing daily frequency ('D').                             
           INFO     Backtesting 4 rule combinations for JKCEMENT                                                       
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 902 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 87 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'JKCEMENT' generated only 8    
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 28 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 611 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.16s                                                         
           WARNING  Could not infer frequency for RAMCOCEM. Forcing daily frequency ('D').                             
           INFO     Backtesting 4 rule combinations for RAMCOCEM                                                       
           INFO     Rule 'engulfing_pattern' generated 25 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 25 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 846 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 25 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 88 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'RAMCOCEM' generated only 4    
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 25 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 575 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for SAIL. Forcing daily frequency ('D').                                 
           INFO     Backtesting 4 rule combinations for SAIL                                                           
           INFO     Rule 'engulfing_pattern' generated 14 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 34 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 14 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 921 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 34 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 14 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 80 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 34 signals on 1093 data points                                    
           WARNING  Low win rate detected for SAIL: 0.0% with 1 trades                                                 
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_volume_spike                            
           WARNING  Average PnL: -177.36, Sharpe: 0.00                                                                 
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'SAIL' generated only 1 trades,
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 14 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 560 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 34 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_uptrend_context' on 'SAIL' generated only 7     
                    trades, which is below the threshold of 10.                                                        
           INFO     find_optimal_strategies completed in 0.14s                                                         
           WARNING  Could not infer frequency for NMDC. Forcing daily frequency ('D').                                 
           INFO     Backtesting 4 rule combinations for NMDC                                                           
           INFO     Rule 'engulfing_pattern' generated 18 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 18 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 915 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 18 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 79 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Low win rate detected for NMDC: 0.0% with 2 trades                                                 
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_volume_spike                            
           WARNING  Average PnL: -4288.98, Sharpe: -0.84                                                               
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'NMDC' generated only 2 trades,
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 18 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 626 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Low win rate detected for NMDC: 18.2% with 11 trades                                               
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_uptrend_context                         
           WARNING  Average PnL: -1149.24, Sharpe: -0.39                                                               
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for ADANIENT. Forcing daily frequency ('D').                             
           INFO     Backtesting 4 rule combinations for ADANIENT                                                       
           INFO     Rule 'engulfing_pattern' generated 13 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 13 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 862 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 13 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 96 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'ADANIENT' generated only 5    
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 13 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 542 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_uptrend_context' on 'ADANIENT' generated only 7 
                    trades, which is below the threshold of 10.                                                        
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for ADANIGREEN. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for ADANIGREEN                                                     
           INFO     Rule 'engulfing_pattern' generated 19 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 19 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 822 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
[01:46:33] INFO     Rule 'engulfing_pattern' generated 19 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 114 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'ADANIGREEN' generated only 4  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 19 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 511 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_uptrend_context' on 'ADANIGREEN' generated only 
                    7 trades, which is below the threshold of 10.                                                      
           INFO     find_optimal_strategies completed in 0.11s                                                         
           WARNING  Could not infer frequency for NAUKRI. Forcing daily frequency ('D').                               
           INFO     Backtesting 4 rule combinations for NAUKRI                                                         
           INFO     Rule 'engulfing_pattern' generated 32 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 32 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 900 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 32 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 77 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           WARNING  Low win rate detected for NAUKRI: 0.0% with 3 trades                                               
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_volume_spike                            
           WARNING  Average PnL: -4820.73, Sharpe: -1.20                                                               
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'NAUKRI' generated only 3      
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 32 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 629 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for POLICYBZR. Forcing daily frequency ('D').                            
           INFO     Backtesting 4 rule combinations for POLICYBZR                                                      
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 911 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 105 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'POLICYBZR' generated only 3   
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 634 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for PAYTM. Forcing daily frequency ('D').                                
           INFO     Backtesting 4 rule combinations for PAYTM                                                          
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 862 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 108 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'PAYTM' generated only 6       
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 608 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.11s                                                         
           WARNING  Could not infer frequency for TITAN. Forcing daily frequency ('D').                                
           INFO     Backtesting 4 rule combinations for TITAN                                                          
           INFO     Rule 'engulfing_pattern' generated 25 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 23 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 25 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 871 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 23 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 25 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 65 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 23 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'TITAN' generated only 3       
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 25 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 625 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 23 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for TRENT. Forcing daily frequency ('D').                                
           INFO     Backtesting 4 rule combinations for TRENT                                                          
           INFO     Rule 'engulfing_pattern' generated 20 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 20 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 943 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 20 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 79 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'TRENT' generated only 5       
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 20 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 735 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for DMART. Forcing daily frequency ('D').                                
           INFO     Backtesting 4 rule combinations for DMART                                                          
           INFO     Rule 'engulfing_pattern' generated 25 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 25 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 803 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 25 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 78 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           WARNING  Low win rate detected for DMART: 0.0% with 5 trades                                                
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_volume_spike                            
           WARNING  Average PnL: -3651.48, Sharpe: -1.03                                                               
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'DMART' generated only 5       
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 25 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 524 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.17s                                                         
           WARNING  Could not infer frequency for JUBLFOOD. Forcing daily frequency ('D').                             
           INFO     Backtesting 4 rule combinations for JUBLFOOD                                                       
           INFO     Rule 'engulfing_pattern' generated 33 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 33 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 827 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 33 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 89 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
[01:46:34] WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'JUBLFOOD' generated only 9    
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 33 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 590 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.15s                                                         
           WARNING  Could not infer frequency for PIDILITIND. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for PIDILITIND                                                     
           INFO     Rule 'engulfing_pattern' generated 21 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 32 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 21 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 870 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 32 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 21 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 52 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 32 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'PIDILITIND' generated only 1  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 21 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 619 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 32 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for UPL. Forcing daily frequency ('D').                                  
           INFO     Backtesting 4 rule combinations for UPL                                                            
           INFO     Rule 'engulfing_pattern' generated 26 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 26 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 808 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 26 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 86 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'UPL' generated only 4 trades, 
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 26 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 545 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for AARTIIND. Forcing daily frequency ('D').                             
           INFO     Backtesting 4 rule combinations for AARTIIND                                                       
           INFO     Rule 'engulfing_pattern' generated 20 signals on 1094 data points                                  
           INFO     Rule 'sma_cross_under' generated 30 signals on 1094 data points                                    
           INFO     Rule 'engulfing_pattern' generated 20 signals on 1094 data points                                  
           INFO     Rule 'rsi_oversold' generated 763 signals on 1094 data points                                      
           INFO     Rule 'sma_cross_under' generated 30 signals on 1094 data points                                    
           INFO     Rule 'engulfing_pattern' generated 20 signals on 1094 data points                                  
           INFO     Rule 'volume_spike' generated 91 signals on 1094 data points                                       
           INFO     Rule 'sma_cross_under' generated 30 signals on 1094 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'AARTIIND' generated only 4    
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 20 signals on 1094 data points                                  
           INFO     Rule 'price_above_sma' generated 534 signals on 1094 data points                                   
           INFO     Rule 'sma_cross_under' generated 30 signals on 1094 data points                                    
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for BALKRISIND. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for BALKRISIND                                                     
           INFO     Rule 'engulfing_pattern' generated 31 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 31 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 837 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 31 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 87 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           WARNING  Low win rate detected for BALKRISIND: 16.7% with 6 trades                                          
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_volume_spike                            
           WARNING  Average PnL: -724.68, Sharpe: -0.14                                                                
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'BALKRISIND' generated only 6  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 31 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 549 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.17s                                                         
           WARNING  Could not infer frequency for MOTHERSON. Forcing daily frequency ('D').                            
           INFO     Backtesting 4 rule combinations for MOTHERSON                                                      
           INFO     Rule 'engulfing_pattern' generated 17 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 17 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 863 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 17 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 90 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'MOTHERSON' generated only 4   
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 17 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 600 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for BOSCHLTD. Forcing daily frequency ('D').                             
           INFO     Backtesting 4 rule combinations for BOSCHLTD                                                       
           INFO     Rule 'engulfing_pattern' generated 24 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 24 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 892 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 24 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 74 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           WARNING  Low win rate detected for BOSCHLTD: 0.0% with 3 trades                                             
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_volume_spike                            
           WARNING  Average PnL: -2821.66, Sharpe: -1.00                                                               
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'BOSCHLTD' generated only 3    
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 24 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 618 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 27 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for MFSL. Forcing daily frequency ('D').                                 
           INFO     Backtesting 4 rule combinations for MFSL                                                           
           INFO     Rule 'engulfing_pattern' generated 36 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 32 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 36 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 871 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 32 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 36 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 107 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 32 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'MFSL' generated only 9 trades,
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 36 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 588 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 32 signals on 1093 data points                                    
[01:46:35] INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for BANDHANBNK. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for BANDHANBNK                                                     
           INFO     Rule 'engulfing_pattern' generated 14 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 14 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 805 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 14 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 91 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Low win rate detected for BANDHANBNK: 0.0% with 1 trades                                           
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_volume_spike                            
           WARNING  Average PnL: -2312.06, Sharpe: -0.15                                                               
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'BANDHANBNK' generated only 1  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 14 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 515 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_uptrend_context' on 'BANDHANBNK' generated only 
                    8 trades, which is below the threshold of 10.                                                      
           INFO     find_optimal_strategies completed in 0.20s                                                         
           WARNING  Could not infer frequency for FEDERALBNK. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for FEDERALBNK                                                     
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 37 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 920 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 37 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 70 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 37 signals on 1093 data points                                    
           WARNING  Low win rate detected for FEDERALBNK: 0.0% with 1 trades                                           
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_volume_spike                            
           WARNING  Average PnL: -4144.66, Sharpe: -0.69                                                               
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'FEDERALBNK' generated only 1  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 27 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 623 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 37 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for IDFCFIRSTB. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for IDFCFIRSTB                                                     
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 882 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 72 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'IDFCFIRSTB' generated only 4  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 600 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for CANBK. Forcing daily frequency ('D').                                
           INFO     Backtesting 4 rule combinations for CANBK                                                          
           INFO     Rule 'engulfing_pattern' generated 18 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 18 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 934 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 18 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 78 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'CANBK' generated only 5       
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 18 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 641 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_uptrend_context' on 'CANBK' generated only 9    
                    trades, which is below the threshold of 10.                                                        
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for PNB. Forcing daily frequency ('D').                                  
           INFO     Backtesting 4 rule combinations for PNB                                                            
           INFO     Rule 'engulfing_pattern' generated 10 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 10 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 911 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 10 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 80 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'PNB' generated only 4 trades, 
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 10 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 630 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_uptrend_context' on 'PNB' generated only 8      
                    trades, which is below the threshold of 10.                                                        
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for BANKBARODA. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for BANKBARODA                                                     
           INFO     Rule 'engulfing_pattern' generated 35 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 35 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 916 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 35 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 80 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'BANKBARODA' generated only 7  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 35 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 652 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 30 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for GMRAIRPORT. Forcing daily frequency ('D').                           
           INFO     Backtesting 4 rule combinations for GMRAIRPORT                                                     
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1094 data points                                  
           INFO     Rule 'sma_cross_under' generated 29 signals on 1094 data points                                    
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1094 data points                                  
           INFO     Rule 'rsi_oversold' generated 889 signals on 1094 data points                                      
           INFO     Rule 'sma_cross_under' generated 29 signals on 1094 data points                                    
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1094 data points                                  
           INFO     Rule 'volume_spike' generated 78 signals on 1094 data points                                       
           INFO     Rule 'sma_cross_under' generated 29 signals on 1094 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'GMRAIRPORT' generated only 5  
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1094 data points                                  
           INFO     Rule 'price_above_sma' generated 587 signals on 1094 data points                                   
           INFO     Rule 'sma_cross_under' generated 29 signals on 1094 data points                                    
[01:46:36] INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for LTF. Forcing daily frequency ('D').                                  
           INFO     Backtesting 4 rule combinations for LTF                                                            
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1094 data points                                  
           INFO     Rule 'sma_cross_under' generated 28 signals on 1094 data points                                    
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1094 data points                                  
           INFO     Rule 'rsi_oversold' generated 913 signals on 1094 data points                                      
           INFO     Rule 'sma_cross_under' generated 28 signals on 1094 data points                                    
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1094 data points                                  
           INFO     Rule 'volume_spike' generated 87 signals on 1094 data points                                       
           INFO     Rule 'sma_cross_under' generated 28 signals on 1094 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'LTF' generated only 3 trades, 
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 23 signals on 1094 data points                                  
           INFO     Rule 'price_above_sma' generated 677 signals on 1094 data points                                   
           INFO     Rule 'sma_cross_under' generated 28 signals on 1094 data points                                    
           INFO     find_optimal_strategies completed in 0.12s                                                         
           WARNING  Could not infer frequency for CHOLAFIN. Forcing daily frequency ('D').                             
           INFO     Backtesting 4 rule combinations for CHOLAFIN                                                       
           INFO     Rule 'engulfing_pattern' generated 16 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 16 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 913 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 16 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 89 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'CHOLAFIN' generated only 5    
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 16 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 601 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 29 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.17s                                                         
           WARNING  Could not infer frequency for PFC. Forcing daily frequency ('D').                                  
           INFO     Backtesting 4 rule combinations for PFC                                                            
           INFO     Rule 'engulfing_pattern' generated 22 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 22 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 950 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 22 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 89 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'PFC' generated only 1 trades, 
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 22 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 647 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for RECLTD. Forcing daily frequency ('D').                               
           INFO     Backtesting 4 rule combinations for RECLTD                                                         
           INFO     Rule 'engulfing_pattern' generated 17 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 17 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 943 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 17 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 97 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           WARNING  Low win rate detected for RECLTD: 0.0% with 1 trades                                               
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_volume_spike                            
           WARNING  Average PnL: -5657.83, Sharpe: -0.67                                                               
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'RECLTD' generated only 1      
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 17 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 652 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 28 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.30s                                                         
           WARNING  Could not infer frequency for IRCTC. Forcing daily frequency ('D').                                
           INFO     Backtesting 4 rule combinations for IRCTC                                                          
           INFO     Rule 'engulfing_pattern' generated 20 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 20 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 879 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 20 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 80 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Low win rate detected for IRCTC: 0.0% with 1 trades                                                
           WARNING  Rule combination: bullish_engulfing_reversal + filter_with_volume_spike                            
           WARNING  Average PnL: -4126.81, Sharpe: -0.57                                                               
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'IRCTC' generated only 1       
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 20 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 576 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.14s                                                         
           WARNING  Could not infer frequency for CDSL. Forcing daily frequency ('D').                                 
           INFO     Backtesting 4 rule combinations for CDSL                                                           
           INFO     Rule 'engulfing_pattern' generated 12 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 12 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 864 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 12 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 98 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'CDSL' generated only 2 trades,
                    which is below the threshold of 10.                                                                
[01:46:37] INFO     Rule 'engulfing_pattern' generated 12 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 573 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 35 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_uptrend_context' on 'CDSL' generated only 6     
                    trades, which is below the threshold of 10.                                                        
           INFO     find_optimal_strategies completed in 0.14s                                                         
           WARNING  Could not infer frequency for CAMS. Forcing daily frequency ('D').                                 
           INFO     Backtesting 4 rule combinations for CAMS                                                           
           INFO     Rule 'engulfing_pattern' generated 15 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 36 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 15 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 916 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 36 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 15 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 94 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 36 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'CAMS' generated only 4 trades,
                    which is below the threshold of 10.                                                                
           INFO     Rule 'engulfing_pattern' generated 15 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 623 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 36 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.13s                                                         
           WARNING  Could not infer frequency for PAGEIND. Forcing daily frequency ('D').                              
           INFO     Backtesting 4 rule combinations for PAGEIND                                                        
           INFO     Rule 'engulfing_pattern' generated 22 signals on 1093 data points                                  
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 22 signals on 1093 data points                                  
           INFO     Rule 'rsi_oversold' generated 804 signals on 1093 data points                                      
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     Rule 'engulfing_pattern' generated 22 signals on 1093 data points                                  
           INFO     Rule 'volume_spike' generated 80 signals on 1093 data points                                       
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           WARNING  Strategy 'bullish_engulfing_reversal + filter_with_volume_spike' on 'PAGEIND' generated only 4     
                    trades, which is below the threshold of 10.                                                        
           INFO     Rule 'engulfing_pattern' generated 22 signals on 1093 data points                                  
           INFO     Rule 'price_above_sma' generated 498 signals on 1093 data points                                   
           INFO     Rule 'sma_cross_under' generated 31 signals on 1093 data points                                    
           INFO     find_optimal_strategies completed in 0.15s                                                         
Saving strategies to database...
           INFO     Saving 256 strategies to the database.                                                             
           INFO     Successfully saved 256 strategies                                                                  
✅ Saved 256 strategies to database
✅ Recalculation complete!
📊 Total strategies evaluated: 256
🎯 Optimal strategies found: 90
💾 Database updated: data\kiss_signal.db

```

## Summary

- **Database cleared:** 0 strategies removed
- **Strategies evaluated:** 256
- **Optimal strategies found:** 90
- **Status:** ✅ Completed

## Next Steps

1. Run `python run.py analyze-strategies` to generate performance report
2. Check `strategy_performance_report.csv` for updated results
3. Review win rates and edge scores for improvements
