import React, { useState, useEffect, useCallback, useRef } from 'react';
import CountUp from 'react-countup';
import './App.css';

// 定义API基础URL
const API_BASE_URL = 'http://38.175.194.75:8000';

interface MetricData {
  totalCashValue: number;
  currentTotalReturn: number;
  createdAt: string;
}

interface CryptoPricing {
  btc: { current_price: number };
  eth: { current_price: number };
  sol: { current_price: number };
  bnb: { current_price: number };
  doge: { current_price: number };
}

// 定义聊天记录接口
interface ChatData {
  id: string;
  model: string;
  chat: any;
  reasoning: string;
  user_prompt: string;
  created_at: string;
  updated_at: string;
}

// 添加已完成交易的接口
interface CompletedTrade {
  id: string;
  symbol: string;
  operation: string;
  leverage: number | null;
  amount: number | null;
  pricing: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  created_at: string;
  chat_id: string;
  chat_model: string | null;
  chat_created_at: string | null;
}

// 添加价格变化历史记录的状态类型
interface PriceHistory {
  [key: string]: number[];
}

// 数字动画组件
const DigitAnimator: React.FC<{ 
  previousDigit: string; 
  currentDigit: string; 
  changed: boolean;
  animationClass: string;
}> = ({ previousDigit, currentDigit, changed, animationClass }) => {
  if (!changed) {
    return <span>{currentDigit}</span>;
  }

  return (
    <span className={animationClass}>
      {currentDigit}
    </span>
  );
};

// 价格动画组件
const PriceAnimator: React.FC<{ 
  symbol: string;
  previousPrice: number;
  currentPrice: number;
}> = React.memo(({ symbol, previousPrice, currentPrice }) => {
  // 首先检查价格是否真正不同
  const arePricesEqual = (a: number, b: number): boolean => {
    return Math.abs(a - b) < 0.0001;
  };
  
  // 如果价格相同，直接返回静态价格显示
  if (arePricesEqual(previousPrice, currentPrice)) {
    const formatPrice = (price: number) => {
      if (symbol === 'DOGE') {
        return price.toFixed(4);
      }
      return price.toFixed(2);
    };
    
    const currentFormatted = formatPrice(currentPrice);
    
    return (
      <span className="price-animator">
        {'$'}
        {currentFormatted}
      </span>
    );
  }
  
  // 格式化价格
  const formatPrice = (price: number) => {
    if (symbol === 'DOGE') {
      return price.toFixed(4);
    }
    return price.toFixed(2);
  };

  const previousFormatted = formatPrice(previousPrice);
  const currentFormatted = formatPrice(currentPrice);
  
  // 分解价格为各个数字位
  const getPriceDigits = (price: string) => {
    return price.split('');
  };
  
  const previousDigits = getPriceDigits(previousFormatted);
  const currentDigits = getPriceDigits(currentFormatted);
  
  // 确定哪些位数发生了变化
  const getChangedPositions = (): boolean[] => {
    const changed: boolean[] = [];
    const maxLength = Math.max(previousDigits.length, currentDigits.length);
    
    for (let i = 0; i < maxLength; i++) {
      const prevDigit = previousDigits[previousDigits.length - 1 - i] || '';
      const currDigit = currentDigits[currentDigits.length - 1 - i] || '';
      changed.unshift(prevDigit !== currDigit);
    }
    
    return changed;
  };
  
  const changedPositions = getChangedPositions();
  
  // 判断价格变化方向
  const isPriceUp = currentPrice > previousPrice;
  const isPriceDown = currentPrice < previousPrice;
  
  return (
    <span className="price-animator">
      {'$'}
      {currentDigits.map((digit, index) => {
        const changed = changedPositions[index] || false;
        const animationClass = changed 
          ? isPriceUp 
            ? 'digit-change-up' 
            : isPriceDown 
              ? 'digit-change-down' 
              : ''
          : '';
          
        return (
          <DigitAnimator
            key={index}
            previousDigit={previousDigits[index] || ''}
            currentDigit={digit}
            changed={changed}
            animationClass={animationClass}
          />
        );
      })}
    </span>
  );
}, (prevProps, nextProps) => {
  // 自定义比较函数，只有当价格真正变化时才重新渲染
  const arePricesEqual = (a: number, b: number): boolean => {
    return Math.abs(a - b) < 0.0001;
  };
  
  return prevProps.symbol === nextProps.symbol && 
         arePricesEqual(prevProps.previousPrice, nextProps.previousPrice) && 
         arePricesEqual(prevProps.currentPrice, nextProps.currentPrice);
});

function App() {
  const [metricsData, setMetricsData] = useState<MetricData[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [pricing, setPricing] = useState<CryptoPricing | null>(null);
  const [chats, setChats] = useState<ChatData[]>([]); // 添加聊天记录状态
  const [completedTrades, setCompletedTrades] = useState<CompletedTrade[]>([]); // 添加已完成交易状态
  const [loading, setLoading] = useState<boolean>(true);
  const [pricingLoading, setPricingLoading] = useState<boolean>(true);
  const [chatsLoading, setChatsLoading] = useState<boolean>(true); // 添加聊天记录加载状态
  const [completedTradesLoading, setCompletedTradesLoading] = useState<boolean>(true); // 添加已完成交易加载状态
  const [error, setError] = useState<string | null>(null);
  const [pricingError, setPricingError] = useState<string | null>(null);
  const [chatsError, setChatsError] = useState<string | null>(null); // 添加聊天记录错误状态
  const [completedTradesError, setCompletedTradesError] = useState<string | null>(null); // 添加已完成交易错误状态
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const [activeTab, setActiveTab] = useState<string>('MODEL CHAT'); // 添加活动标签状态
  
  // 添加价格历史记录状态
  const [priceHistory, setPriceHistory] = useState<PriceHistory>({});
  
  // 用于比较数据变化的引用
  const prevMetricsDataRef = useRef<MetricData[]>([]);
  const prevPricingRef = useRef<CryptoPricing | null>(null);

  // 深度比较函数，用于检测数据是否真正发生变化
  const deepEqual = (obj1: any, obj2: any): boolean => {
    if (obj1 === obj2) return true;
    if (obj1 === null || obj2 === null) return false;
    if (typeof obj1 !== 'object' || typeof obj2 !== 'object') return false;
    
    const keys1 = Object.keys(obj1);
    const keys2 = Object.keys(obj2);
    
    if (keys1.length !== keys2.length) return false;
    
    for (let key of keys1) {
      if (!keys2.includes(key)) return false;
      if (!deepEqual(obj1[key], obj2[key])) return false;
    }
    
    return true;
  };

  // 获取图表数据
  const fetchMetrics = useCallback(async () => {
    try {
      setError(null);
      const response = await fetch(`${API_BASE_URL}/api/metrics`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      if (data.success && data.data) {
        // 只有在数据真正发生变化时才更新状态
        const newMetricsData = data.data.metrics || [];
        const newTotalCount = data.data.totalCount || 0;
        
        // 优化：即使数据相同也更新最后更新时间，让用户知道系统在正常运行
        setLastUpdate(new Date().toLocaleTimeString());
        
        if (!deepEqual(newMetricsData, prevMetricsDataRef.current) || 
            newTotalCount !== totalCount) {
          setMetricsData(newMetricsData);
          setTotalCount(newTotalCount);
          prevMetricsDataRef.current = newMetricsData;
        }
      }
    } catch (err) {
      console.error('Error fetching metrics:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch metrics');
    } finally {
      setLoading(false);
    }
  }, [totalCount]);

  // 获取价格数据（使用优化的API端点）
  const fetchPricing = useCallback(async () => {
    try {
      setPricingError(null);
      setPricingLoading(true);
      // 使用简化的价格API端点，只获取当前价格
      const response = await fetch(`${API_BASE_URL}/api/pricing/simple`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      if (data.success && data.data.pricing) {
        const newPricing = data.data.pricing as CryptoPricing;
        
        // 检查是否有任何价格发生了变化
        const symbols = ['btc', 'eth', 'sol', 'bnb', 'doge'];
        let hasAnyPriceChanged = false;
        
        // 检查每个货币的价格是否发生变化
        for (const symbol of symbols) {
          const currentPrice = newPricing[symbol]?.current_price || 0;
          const previousPrice = prevPricingRef.current?.[symbol]?.current_price || 0;
          
          // 使用更安全的浮点数比较
          const arePricesEqual = (a: number, b: number): boolean => {
            return Math.abs(a - b) < 0.0001;
          };
          
          if (!arePricesEqual(currentPrice, previousPrice)) {
            hasAnyPriceChanged = true;
            break;
          }
        }
        
        // 只有当有任何价格发生变化时才更新状态和历史记录
        if (hasAnyPriceChanged) {
          // 更新价格历史记录
          const newPriceHistory = { ...priceHistory };
          let hasHistoryUpdated = false;
          
          symbols.forEach(symbol => {
            const currentPrice = newPricing[symbol]?.current_price || 0;
            const previousPrice = prevPricingRef.current?.[symbol]?.current_price || 0;
            
            // 使用更安全的浮点数比较
            const arePricesEqual = (a: number, b: number): boolean => {
              return Math.abs(a - b) < 0.0001;
            };
            
            // 只有当价格真正发生变化时才更新历史记录
            if (!arePricesEqual(currentPrice, previousPrice)) {
              if (!newPriceHistory[symbol]) {
                newPriceHistory[symbol] = [];
              }
              
              // 只保留最近5个价格点用于动画
              newPriceHistory[symbol] = [...newPriceHistory[symbol].slice(-4), currentPrice];
              hasHistoryUpdated = true;
            }
          });
          
          // 只有当历史记录真正更新时才设置状态
          if (hasHistoryUpdated) {
            setPriceHistory(newPriceHistory);
            setPricing(newPricing);
            prevPricingRef.current = newPricing;
          }
        }
        // 如果没有任何价格变化，不更新任何状态
      }
    } catch (err) {
      console.error('Error fetching pricing:', err);
      setPricingError(err instanceof Error ? err.message : 'Failed to fetch pricing');
    } finally {
      setPricingLoading(false);
    }
  }, [priceHistory]);

  // 获取聊天记录数据
  const fetchChats = useCallback(async () => {
    try {
      // setChatsLoading(true);
      setChatsError(null);
      const response = await fetch(`${API_BASE_URL}/api/trading/chats`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      if (data.success && data.data) {
        setChats(data.data);
      }
    } catch (err) {
      console.error('Error fetching chats:', err);
      setChatsError(err instanceof Error ? err.message : 'Failed to fetch chats');
      // 不要清除现有数据，即使获取新数据失败
    } finally {
      // setChatsLoading(false);
    }
  }, []);

  // 获取已完成交易数据
  const fetchCompletedTrades = useCallback(async () => {
    try {
      setCompletedTradesLoading(true);
      setCompletedTradesError(null);
      const response = await fetch(`${API_BASE_URL}/api/trading/completed-trades`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      if (data.success && data.data) {
        setCompletedTrades(data.data);
      }
    } catch (err) {
      console.error('Error fetching completed trades:', err);
      setCompletedTradesError(err instanceof Error ? err.message : 'Failed to fetch completed trades');
    } finally {
      setCompletedTradesLoading(false);
    }
  }, []);

  useEffect(() => {
    // 初始加载
    fetchMetrics();
    fetchPricing();
    
    // 如果MODEL CHAT标签是活动的，也获取聊天记录
    if (activeTab === 'MODEL CHAT') {
      fetchChats();
    }
    
    // 如果COMPLETED TRADES标签是活动的，也获取已完成交易数据
    if (activeTab === 'COMPLETED TRADES') {
      fetchCompletedTrades();
    }

    // 优化指标获取频率：从10秒增加到20秒，减轻服务器压力
    const metricsInterval = setInterval(fetchMetrics, 20000);
    // 价格更新频率可以更高，因为使用了优化的API
    const pricingInterval = setInterval(fetchPricing, 5000);
    
    // 聊天记录更新频率 - 每3分钟更新一次
    const chatsInterval = setInterval(() => {
      if (activeTab === 'MODEL CHAT') {
        fetchChats();
      }
    }, 180000); // 3分钟 = 180000毫秒
    
    // 已完成交易更新频率 - 每3分钟更新一次
    const tradesInterval = setInterval(() => {
      if (activeTab === 'COMPLETED TRADES') {
        fetchCompletedTrades();
      }
    }, 180000); // 3分钟 = 180000毫秒

    return () => {
      clearInterval(metricsInterval);
      clearInterval(pricingInterval);
      clearInterval(chatsInterval);
      clearInterval(tradesInterval);
    };
  }, [fetchMetrics, fetchPricing, fetchChats, fetchCompletedTrades, activeTab]);

  // 简化的图表组件
  const SimpleChart = ({ data }: { data: MetricData[] }) => {
    if (!data || data.length === 0) return <div className="no-data">No chart data available</div>;
    
    const maxValue = Math.max(...data.map(d => d.totalCashValue));
    const minValue = Math.min(...data.map(d => d.totalCashValue));
    const range = maxValue - minValue || 1;
    
    return (
      <div className="chart-container">
        <div className="chart-header">
          <h3>TOTAL ACCOUNT VALUE</h3>
          <div className="chart-controls">
            <button className="time-range active">ALL</button>
            <button className="time-range">72H</button>
          </div>
        </div>
        <svg width="100%" height="300" viewBox="0 0 800 300">
          <defs>
            <linearGradient id="chartGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#0066FF" stopOpacity="0.2" />
              <stop offset="100%" stopColor="#0066FF" stopOpacity="0" />
            </linearGradient>
          </defs>
          <polygon
            fill="url(#chartGradient)"
            points={`0,250 ${data.map((d, i) => {
              const x = (i / (data.length - 1)) * 800;
              const y = 250 - ((d.totalCashValue - minValue) / range) * 200;
              return `${x},${y}`;
            }).join(' ')} 800,250`}
          />
          <polyline
            fill="none"
            stroke="#0066FF"
            strokeWidth="2"
            points={data.map((d, i) => {
              const x = (i / (data.length - 1)) * 800;
              const y = 250 - ((d.totalCashValue - minValue) / range) * 200;
              return `${x},${y}`;
            }).join(' ')}
          />
          {data.map((d, i) => {
            const x = (i / (data.length - 1)) * 800;
            const y = 250 - ((d.totalCashValue - minValue) / range) * 200;
            return (
              <circle
                key={i}
                cx={x}
                cy={y}
                r={i === data.length - 1 ? 4 : 2}
                fill={i === data.length - 1 ? "#0066FF" : "#fff"}
                stroke="#0066FF"
                strokeWidth={i === data.length - 1 ? 2 : 1}
              />
            );
          })}
        </svg>
        <div className="chart-stats">
          <div className="stat-item">
            <span className="stat-label">CURRENT</span>
            <span className="stat-value">
              ${metricsData.length > 0 ? metricsData[metricsData.length - 1].totalCashValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}
            </span>
          </div>
          <div className="stat-item">
            <span className="stat-label">RETURN</span>
            <span className={`stat-value ${metricsData.length > 0 && metricsData[metricsData.length - 1].currentTotalReturn >= 0 ? 'positive' : 'negative'}`}>
              {metricsData.length > 0 ? `${metricsData[metricsData.length - 1].currentTotalReturn.toFixed(2)}%` : '0.00%'}
            </span>
          </div>
        </div>
      </div>
    );
  };

  // 聊天记录组件
  const ChatList = () => {
    // 添加状态来跟踪每个聊天项的展开状态
    const [expandedStates, setExpandedStates] = useState<{[key: string]: boolean}>({});

    // 切换聊天项的展开状态
    const toggleExpand = (chatId: string) => {
      setExpandedStates(prev => ({
        ...prev,
        [chatId]: !prev[chatId]
      }));
    };

    // 修改这里：即使在加载中也不显示转圈动画
    if (chatsLoading) {
      // 如果已经有聊天数据，即使在后台加载新数据也不显示加载状态
      if (chats && chats.length > 0) {
        // 继续显示现有数据
      } else {
        // 只有在完全没有数据时才显示加载状态
        return (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading chat history...</p>
          </div>
        );
      }
    }

    if (chatsError) {
      return (
        <div className="error-state">
          <p>Error loading chat history: {chatsError}</p>
        </div>
      );
    }

    if (!chats || chats.length === 0) {
      return (
        <div className="no-data-state">
          <p>No chat history available</p>
        </div>
      );
    }

    // 限制最多展示10条会话
    const limitedChats = chats.slice(0, 10);

    return (
      <div className="chat-list">
        {limitedChats.map((chat) => (
          <div key={chat.id} className="chat-item">
            <div className="chat-header">
              <span className="chat-model">{chat.model}</span>
              <span className="chat-time">
                {new Date(chat.created_at).toLocaleString()}
              </span>
              <button 
                className="expand-toggle"
                onClick={() => toggleExpand(chat.id)}
              >
                {expandedStates[chat.id] ? 'Hide Prompt' : 'Show Prompt'}
              </button>
            </div>
            <div className="chat-content">
              <div className="chat-decision">
                <strong>Decision:</strong>
                <pre>{JSON.stringify(chat.chat, null, 2)}</pre>
              </div>
              {/* 默认显示分析内容（推理过程） */}
              <div className="chat-reasoning">
                <strong>Analysis (Reasoning):</strong>
                <div className="reasoning-content">{chat.reasoning}</div>
              </div>
              {/* 点击展开时显示提示词内容 */}
              {expandedStates[chat.id] && (
                <div className="chat-expanded-content">
                  <div className="chat-prompt">
                    <strong>Prompt:</strong> {chat.user_prompt}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };

  // 加密货币卡片组件
  const CryptoCard = React.memo(({ symbol, name, price }: { symbol: string; name: string; price: string }) => {
    // 从价格字符串中提取数值用于动画
    const priceValue = parseFloat(price.replace(/[^0-9.-]+/g, "")) || 0;
    
    // 获取价格历史记录用于动画
    const history = priceHistory[symbol.toLowerCase()] || [];
    const hasHistory = history.length > 1;
    const previousPrice = hasHistory ? history[history.length - 2] : priceValue;
    
    // 判断价格是否发生变化（使用更安全的浮点数比较）
    const arePricesEqual = (a: number, b: number): boolean => {
      return Math.abs(a - b) < 0.0001;
    };
    
    const hasPriceChanged = hasHistory && !arePricesEqual(previousPrice, priceValue);
    
    // 如果没有历史记录或者价格没有变化，直接显示静态价格
    if (!hasHistory || !hasPriceChanged) {
      return (
        <div className="crypto-card">
          <div className="crypto-icon">
            <div className={`coin-icon ${symbol.toLowerCase()}`}>{symbol.charAt(0)}</div>
          </div>
          <div className="crypto-info">
            <div className="symbol">{symbol}</div>
            <div className="name">{name}</div>
          </div>
          <div className="price-container">
            <div className="price">
              {price}
            </div>
          </div>
        </div>
      );
    }
    
    // 如果价格确实发生变化，则使用动画组件
    return (
      <div className="crypto-card">
        <div className="crypto-icon">
          <div className={`coin-icon ${symbol.toLowerCase()}`}>{symbol.charAt(0)}</div>
        </div>
        <div className="crypto-info">
          <div className="symbol">{symbol}</div>
          <div className="name">{name}</div>
        </div>
        <div className="price-container">
          <PriceAnimator 
            symbol={symbol}
            previousPrice={previousPrice}
            currentPrice={priceValue}
          />
        </div>
      </div>
    );
  }, (prevProps, nextProps) => {
    // 自定义比较函数，只有当props真正变化时才重新渲染
    return prevProps.symbol === nextProps.symbol && 
           prevProps.name === nextProps.name && 
           prevProps.price === nextProps.price;
  });

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1 className="app-title">Nof1.ai</h1>
          <p className="app-subtitle">AI trading in real markets</p>
          {lastUpdate && <div className="last-update">Last updated: {lastUpdate}</div>}
        </div>
      </header>

      {/* 错误提示 */}
      {(error || pricingError || chatsError) && (
        <div className="alerts-container">
          {error && <div className="alert error">Metrics Error: {error}</div>}
          {pricingError && <div className="alert error">Pricing Error: {pricingError}</div>}
          {chatsError && <div className="alert error">Chats Error: {chatsError}</div>}
        </div>
      )}

      {/* 加密货币行情 */}
      <section className="crypto-pricing-section">
        <div className="section-header">
          <h2>CRYPTO PRICING</h2>
        </div>
        <div className="crypto-grid">
          {pricingError ? (
            <div className="error-state">
              <p>Error loading pricing data</p>
            </div>
          ) : pricing ? (
            <>
              <CryptoCard
                symbol="BTC"
                name="Bitcoin"
                price={`$${pricing.btc?.current_price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
              />
              <CryptoCard
                symbol="ETH"
                name="Ethereum"
                price={`$${pricing.eth?.current_price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
              />
              <CryptoCard
                symbol="SOL"
                name="Solana"
                price={`$${pricing.sol?.current_price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
              />
              <CryptoCard
                symbol="BNB"
                name="BNB"
                price={`$${pricing.bnb?.current_price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
              />
              <CryptoCard
                symbol="DOGE"
                name="Dogecoin"
                price={`$${pricing.doge?.current_price?.toFixed(4)}`}
              />
            </>
          ) : (
            <div className="no-data-state">
              <p>No pricing data available</p>
            </div>
          )}
        </div>
      </section>

      {/* 主要内容区域 - 左侧图表，右侧标签页内容 */}
      <div className="main-layout">
        {/* 左侧图表面板 */}
        <div className="chart-panel">
          <div className="chart-panel-header">
            <h2>PERFORMANCE CHART</h2>
            <p>Real-time tracking • Updates every 10s</p>
          </div>
          {loading ? (
            <div className="loading-state chart-loading">
              <div className="spinner"></div>
              <p>Loading chart data...</p>
            </div>
          ) : error ? (
            <div className="error-state">
              <p>Error loading chart data</p>
            </div>
          ) : (
            <>
              <SimpleChart data={metricsData} />
              <div className="data-points">{metricsData.length} of {totalCount.toLocaleString()} points</div>
            </>
          )}
        </div>

        {/* 右侧内容面板 */}
        <div className="content-panel">
          {/* 导航区域 */}
          <nav className="app-nav">
            <ul className="nav-list">
              <li 
                className={`nav-item ${activeTab === 'MODEL CHAT' ? 'active' : ''}`}
                onClick={() => setActiveTab('MODEL CHAT')}
              >
                MODEL CHAT
              </li>
              <li 
                className={`nav-item ${activeTab === 'POSITIONS' ? 'active' : ''}`}
                onClick={() => setActiveTab('POSITIONS')}
              >
                POSITIONS
              </li>
              <li 
                className={`nav-item ${activeTab === 'COMPLETED TRADES' ? 'active' : ''}`}
                onClick={() => setActiveTab('COMPLETED TRADES')}
              >
                COMPLETED TRADES
              </li>
              <li 
                className={`nav-item ${activeTab === 'README.TXT' ? 'active' : ''}`}
                onClick={() => setActiveTab('README.TXT')}
              >
                README.TXT
              </li>
            </ul>
          </nav>

          {/* 标签页内容区域 */}
          <section className="content-section">
            {activeTab === 'MODEL CHAT' && (
              <div className="tab-content">
                <div className="section-header">
                  <h2>MODEL CHAT HISTORY</h2>
                  <p>AI trading decisions and reasoning • Updates every 3 minutes</p>
                </div>
                <ChatList />
              </div>
            )}
            
            {activeTab === 'POSITIONS' && (
              <div className="tab-content">
                <div className="section-header">
                  <h2>CURRENT POSITIONS</h2>
                  <p>Active trading positions</p>
                </div>
                <div className="no-data-state">
                  <p>Position tracking not implemented yet</p>
                </div>
              </div>
            )}
            
            {activeTab === 'COMPLETED TRADES' && (
              <div className="tab-content">
                <div className="section-header">
                  <h2>COMPLETED TRADES</h2>
                  <p>Historical trade records</p>
                </div>
                {completedTradesLoading ? (
                  <div className="loading-state">
                    <div className="spinner"></div>
                    <p>Loading completed trades...</p>
                  </div>
                ) : completedTradesError ? (
                  <div className="error-state">
                    <p>Error loading completed trades: {completedTradesError}</p>
                  </div>
                ) : completedTrades && completedTrades.length > 0 ? (
                  <div className="completed-trades-list">
                    {completedTrades.map((trade) => (
                      <div key={trade.id} className="trade-item">
                        <div className="trade-header">
                          <span className={`trade-operation ${trade.operation.toLowerCase()}`}>
                            {trade.operation}
                          </span>
                          <span className="trade-symbol">{trade.symbol}</span>
                          <span className="trade-time">
                            {new Date(trade.created_at).toLocaleString()}
                          </span>
                        </div>
                        <div className="trade-details">
                          {trade.amount && (
                            <div className="trade-detail">
                              <span className="detail-label">Amount:</span>
                              <span className="detail-value">{trade.amount}</span>
                            </div>
                          )}
                          {trade.pricing && (
                            <div className="trade-detail">
                              <span className="detail-label">Price:</span>
                              <span className="detail-value">${trade.pricing}</span>
                            </div>
                          )}
                          {trade.leverage && (
                            <div className="trade-detail">
                              <span className="detail-label">Leverage:</span>
                              <span className="detail-value">{trade.leverage}x</span>
                            </div>
                          )}
                          {trade.stop_loss && (
                            <div className="trade-detail">
                              <span className="detail-label">Stop Loss:</span>
                              <span className="detail-value">${trade.stop_loss}</span>
                            </div>
                          )}
                          {trade.take_profit && (
                            <div className="trade-detail">
                              <span className="detail-label">Take Profit:</span>
                              <span className="detail-value">${trade.take_profit}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="no-data-state">
                    <p>No completed trades available</p>
                  </div>
                )}
              </div>
            )}
            
            {activeTab === 'README.TXT' && (
              <div className="tab-content">
                <div className="section-header">
                  <h2>README.TXT</h2>
                  <p>Project documentation</p>
                </div>
                <div className="readme-content">
                  <h3>Crypto.ai</h3>
                  <p>This is the crypto.ai project, an AI-powered cryptocurrency trading system.</p>
                  <h4>Features:</h4>
                  <ul>
                    <li>Real-time cryptocurrency pricing</li>
                    <li>AI-powered trading decisions</li>
                    <li>Performance tracking charts</li>
                    <li>Automated trading execution</li>
                  </ul>
                  <h4>Technology Stack:</h4>
                  <ul>
                    <li>Frontend: React with TypeScript</li>
                    <li>Backend: FastAPI with Python</li>
                    <li>Database: SQLite</li>
                    <li>AI Model: DeepSeek API</li>
                    <li>Exchange API: Binance</li>
                  </ul>
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

export default App;