// frontend/src/App.tsx
// frontend/src/App.tsx - UPDATED VERSION
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import HumanReview from './components/HumanReview';
import { GraphState, Task } from './types';

const API_URL = 'http://localhost:8000';

// Example intents
const EXAMPLE_INTENTS = [
  "Create a CBT exercise for challenging anxious thoughts",
  "Design a mindfulness exercise for stress reduction",
  "Create an exposure hierarchy for social anxiety",
  "Design a behavioral activation exercise for depression",
  "Create a thought record exercise for cognitive restructuring",
  "Create a sleep hygiene protocol for insomnia",
  "Design a panic attack grounding exercise",
  "Create an exercise for managing perfectionism",
  "Design a self-compassion meditation script",
  "Create a values clarification exercise"
];

function App() {
  // State
  const [intent, setIntent] = useState<string>('');
  const [threadId, setThreadId] = useState<string | null>(null);
  const [status, setStatus] = useState<'idle' | 'processing' | 'halted' | 'completed' | 'error' | 'resuming'>('idle');
  const [currentState, setCurrentState] = useState<GraphState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [showTasks, setShowTasks] = useState(false);
  const [activeTab, setActiveTab] = useState<'generator' | 'history'>('generator');

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

const startPolling = (tid: string) => {
  if (pollIntervalRef.current) {
    clearInterval(pollIntervalRef.current);
  }

  let pollCount = 0;
  pollIntervalRef.current = setInterval(async () => {
    pollCount++;
    console.log(`🔄 Poll #${pollCount} for thread ${tid}`);
    
    try {
      const response = await axios.get(`${API_URL}/state/${tid}`, {
        timeout: 5000
      });
      
      console.log(`📊 Poll response:`, {
        status: response.data.status,
        hasState: !!response.data.state,
        threadId: response.data.thread_id
      });
      
      const { status: newStatus, state } = response.data;
      
      setStatus(newStatus || 'unknown');
      setCurrentState(state || null);
      
      // Stop polling conditions
      if (['completed', 'halted', 'error', 'rejected'].includes(newStatus || '')) {
        console.log(`⏹️ Stopping polling - final status: ${newStatus}`);
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
      }
    } catch (err: any) {
      console.error('❌ Polling error:', err);
      
      // Stop polling after too many errors
      if (pollCount > 10) {
        setStatus('error');
        setError('Polling failed after multiple attempts');
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
      }
    }
  }, 2000); // Poll every 2 seconds
};

  // Fetch all tasks
  const fetchTasks = async () => {
    try {
      const response = await axios.get(`${API_URL}/tasks`);
      if (response.data.success && response.data.data?.tasks) {
        const taskList: Task[] = Object.entries(response.data.data.tasks)
          .map(([thread_id, task]: [string, any]) => ({
            thread_id,
            status: task.status,
            intent: task.intent || 'Unknown',
            created_at: task.created_at,
            iterations: task.iterations || 0
          }))
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        
        setTasks(taskList);
      }
    } catch (err) {
      console.error('Error fetching tasks:', err);
    }
  };

  // Start generation
  const handleInvoke = async () => {
  if (!intent.trim()) {
    alert('Please enter an intent');
    return;
  }

  setStatus('processing');
  setError(null);
  setCurrentState(null);

  try {
    console.log('🔄 Sending request to backend...');
    
    const response = await axios.post(`${API_URL}/invoke`, { 
      intent: intent.trim() 
    }, {
      timeout: 10000, // 10 second timeout
    });

    console.log('✅ Backend response:', response.data);
    
    const newThreadId = response.data.data?.thread_id;
    if (newThreadId) {
      setThreadId(newThreadId);
      console.log(`📋 Thread ID received: ${newThreadId}`);
      startPolling(newThreadId);
    } else {
      throw new Error('No thread_id in response');
    }
  } catch (err: any) {
    console.error('❌ Full error details:', err);
    
    // Detailed error messages
    if (err.code === 'ECONNREFUSED') {
      setError('Cannot connect to backend. Is it running on port 8000?');
    } else if (err.code === 'ERR_NETWORK') {
      setError('Network error. Check CORS and backend URL.');
    } else if (err.response) {
      // Backend returned an error status
      setError(`Backend error ${err.response.status}: ${err.response.data?.message || 'Unknown error'}`);
    } else if (err.request) {
      // Request made but no response
      setError('No response from backend. Check if server is running.');
    } else {
      setError(err.message || 'Failed to start generation');
    }
    
    setStatus('error');
  }
};

  // Handle example click
  const handleExampleClick = (exampleIntent: string) => {
    setIntent(exampleIntent);
  };

  // Clear current task
  const handleClear = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setStatus('idle');
    setThreadId(null);
    setCurrentState(null);
    setError(null);
  };

  // Load a previous task
  const loadTask = async (task: Task) => {
    setThreadId(task.thread_id);
    setStatus(task.status as any);
    setActiveTab('generator');
    
    try {
      const response = await axios.get(`${API_URL}/state/${task.thread_id}`);
      const { state } = response.data.data || {};
      setCurrentState(state);
      
      if (task.status === 'running' || task.status === 'halted') {
        startPolling(task.thread_id);
      }
    } catch (err) {
      console.error('Error loading task:', err);
      setError('Failed to load task');
    }
  };

  // Initialize
  useEffect(() => {
    fetchTasks();
    
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  return (
    <div style={{
      maxWidth: '1200px',
      margin: '0 auto',
      padding: '20px',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
      minHeight: '100vh'
    }}>
      {/* Header */}
      <header style={{
        textAlign: 'center',
        marginBottom: '40px',
        paddingBottom: '20px',
        borderBottom: '2px solid #4a90e2'
      }}>
        <h1 style={{
          color: '#2c3e50',
          fontSize: '2.5rem',
          marginBottom: '10px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '10px'
        }}>
          🧠 Cerina Protocol Foundry
          <span style={{
            fontSize: '0.8rem',
            background: '#4a90e2',
            color: 'white',
            padding: '2px 8px',
            borderRadius: '12px',
            verticalAlign: 'middle'
          }}>
            v2.0
          </span>
        </h1>
        <p style={{
          color: '#7f8c8d',
          fontSize: '1.1rem',
          maxWidth: '800px',
          margin: '0 auto'
        }}>
          Multi-agent system for generating clinically-sound CBT exercises with safety reviews
        </p>
      </header>

      {/* Main Content */}
      <main>
        {/* Tabs */}
        <div style={{
          display: 'flex',
          gap: '10px',
          marginBottom: '20px',
          borderBottom: '1px solid #dee2e6'
        }}>
          <button
            onClick={() => setActiveTab('generator')}
            style={{
              padding: '10px 20px',
              background: activeTab === 'generator' ? '#4a90e2' : 'white',
              color: activeTab === 'generator' ? 'white' : '#495057',
              border: '1px solid #dee2e6',
              borderBottom: activeTab === 'generator' ? '2px solid #4a90e2' : '1px solid #dee2e6',
              borderRadius: '6px 6px 0 0',
              cursor: 'pointer',
              fontSize: '16px',
              marginBottom: '-1px'
            }}
          >
            🚀 Generator
          </button>
          <button
            onClick={() => {
              setActiveTab('history');
              fetchTasks();
            }}
            style={{
              padding: '10px 20px',
              background: activeTab === 'history' ? '#4a90e2' : 'white',
              color: activeTab === 'history' ? 'white' : '#495057',
              border: '1px solid #dee2e6',
              borderBottom: activeTab === 'history' ? '2px solid #4a90e2' : '1px solid #dee2e6',
              borderRadius: '6px 6px 0 0',
              cursor: 'pointer',
              fontSize: '16px',
              marginBottom: '-1px'
            }}
          >
            📋 History ({tasks.length})
          </button>
        </div>

        {/* Generator Tab */}
        {activeTab === 'generator' && (
          <>
            {/* Input Section */}
            <div style={{
              background: 'white',
              borderRadius: '12px',
              padding: '30px',
              boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
              marginBottom: '30px'
            }}>
              <h2 style={{ color: '#2c3e50', marginTop: 0 }}>🎯 Enter Your Intent</h2>
              
              <div style={{ marginBottom: '20px' }}>
                <textarea
                  value={intent}
                  onChange={(e) => setIntent(e.target.value)}
                  placeholder="Describe the CBT exercise you want to create. Be specific about the target issue, population, and goals..."
                  style={{
                    width: '100%',
                    height: '100px',
                    padding: '15px',
                    fontSize: '16px',
                    border: '2px solid #e0e0e0',
                    borderRadius: '8px',
                    resize: 'vertical',
                    fontFamily: 'inherit',
                    lineHeight: '1.5'
                  }}
                  disabled={status === 'processing' || status === 'resuming'}
                />
              </div>

              {/* Example Intents */}
              <div style={{ marginBottom: '20px' }}>
                <h3 style={{ color: '#7f8c8d', fontSize: '1rem', marginBottom: '10px' }}>
                  💡 Quick Examples:
                </h3>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                  {EXAMPLE_INTENTS.map((example, index) => (
                    <button
                      key={index}
                      onClick={() => handleExampleClick(example)}
                      disabled={status === 'processing' || status === 'resuming'}
                      style={{
                        padding: '8px 16px',
                        background: '#e8f4fc',
                        color: '#2980b9',
                        border: '1px solid #4a90e2',
                        borderRadius: '20px',
                        cursor: 'pointer',
                        fontSize: '14px',
                        transition: 'all 0.2s',
                        whiteSpace: 'nowrap'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = '#d4e7f7'}
                      onMouseLeave={(e) => e.currentTarget.style.background = '#e8f4fc'}
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{
                display: 'flex',
                gap: '15px',
                alignItems: 'center'
              }}>
                <button
                  onClick={handleInvoke}
                  disabled={status === 'processing' || status === 'resuming' || !intent.trim()}
                  style={{
                    padding: '15px 30px',
                    background: status === 'processing' || status === 'resuming' ? '#6c757d' : '#4a90e2',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    fontSize: '16px',
                    fontWeight: 'bold',
                    cursor: status === 'processing' || status === 'resuming' ? 'not-allowed' : 'pointer',
                    opacity: status === 'processing' || status === 'resuming' ? 0.7 : 1,
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '10px'
                  }}
                >
                  {status === 'processing' ? (
                    <>
                      <span style={{ animation: 'spin 1s linear infinite' }}>⟳</span>
                      Generating...
                    </>
                  ) : status === 'resuming' ? (
                    '⏳ Finalizing...'
                  ) : (
                    '🚀 Generate Protocol'
                  )}
                </button>
                
                <button
                  onClick={handleClear}
                  style={{
                    padding: '15px 20px',
                    background: 'white',
                    color: '#dc3545',
                    border: '2px solid #dc3545',
                    borderRadius: '8px',
                    fontSize: '16px',
                    cursor: 'pointer'
                  }}
                >
                  Clear
                </button>
              </div>
            </div>

            {/* Status Display */}
            {status !== 'idle' && (
              <div style={{
                background: status === 'error' ? '#f8d7da' : 
                          status === 'processing' ? '#fff3cd' : 
                          status === 'completed' ? '#d4edda' : 
                          status === 'halted' ? '#cce5ff' : '#e8f4fc',
                color: status === 'error' ? '#721c24' : 
                      status === 'processing' ? '#856404' : 
                      status === 'completed' ? '#155724' : 
                      status === 'halted' ? '#004085' : '#2c3e50',
                padding: '15px 20px',
                borderRadius: '8px',
                marginBottom: '20px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div>
                  <strong>Status:</strong> {status.toUpperCase()}
                  {threadId && (
                    <div style={{ fontSize: '12px', marginTop: '5px', fontFamily: 'monospace' }}>
                      Thread ID: {threadId}
                    </div>
                  )}
                </div>
                
                {status === 'processing' && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{
                      width: '20px',
                      height: '20px',
                      border: '3px solid #f3f3f3',
                      borderTop: '3px solid #856404',
                      borderRadius: '50%',
                      animation: 'spin 1s linear infinite'
                    }} />
                    <span>Multi-agent system working...</span>
                  </div>
                )}
              </div>
            )}

            {/* Error Display */}
            {error && (
              <div style={{
                background: '#f8d7da',
                color: '#721c24',
                padding: '15px',
                borderRadius: '8px',
                marginBottom: '20px',
                border: '1px solid #f5c6cb'
              }}>
                <strong>Error:</strong> {error}
              </div>
            )}

            {/* Human Review Section */}
            {status === 'halted' && currentState && threadId && (
              <HumanReview
                threadId={threadId}
                state={currentState}
                onComplete={handleClear}
                onResuming={() => setStatus('resuming')}
              />
            )}

            {/* Final Result */}
            {status === 'completed' && currentState && (
              <div style={{
                background: 'white',
                borderRadius: '12px',
                padding: '30px',
                boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
              }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '20px'
                }}>
                  <h2 style={{ color: '#27ae60', margin: 0 }}>
                    ✅ Protocol Finalized!
                  </h2>
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(currentState.draft);
                        alert('Copied to clipboard!');
                      }}
                      style={{
                        padding: '10px 20px',
                        background: '#27ae60',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer'
                      }}
                    >
                      📋 Copy to Clipboard
                    </button>
                    <button
                      onClick={() => {
                        const blob = new Blob([currentState.draft], { type: 'text/markdown' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `cbt_protocol_${new Date().toISOString().slice(0, 10)}.md`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                      }}
                      style={{
                        padding: '10px 20px',
                        background: '#6c757d',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer'
                      }}
                    >
                      💾 Download
                    </button>
                  </div>
                </div>
                
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '2fr 1fr',
                  gap: '30px'
                }}>
                  {/* Draft Display */}
                  <div style={{
                    border: '1px solid #ddd',
                    borderRadius: '8px',
                    padding: '20px',
                    background: '#f8f9fa',
                    minHeight: '500px',
                    overflowY: 'auto'
                  }}>
                    <ReactMarkdown>{currentState.draft}</ReactMarkdown>
                  </div>
                  
                  {/* Stats Sidebar */}
                  <div>
                    <div style={{
                      background: '#e8f4fc',
                      padding: '20px',
                      borderRadius: '8px',
                      marginBottom: '20px'
                    }}>
                      <h3 style={{ color: '#2980b9', marginTop: 0 }}>📊 Final Scores</h3>
                      <div style={{ marginBottom: '15px' }}>
                        <div style={{ fontSize: '14px', color: '#666' }}>Safety Score</div>
                        <div style={{
                          fontSize: '32px',
                          fontWeight: 'bold',
                          color: currentState.scores.safety >= 8 ? '#27ae60' : '#f39c12'
                        }}>
                          {currentState.scores.safety}/10
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: '14px', color: '#666' }}>Clinical Score</div>
                        <div style={{
                          fontSize: '32px',
                          fontWeight: 'bold',
                          color: currentState.scores.clinical >= 8 ? '#27ae60' : '#f39c12'
                        }}>
                          {currentState.scores.clinical}/10
                        </div>
                      </div>
                    </div>
                    
                    <div style={{
                      background: '#fff3cd',
                      padding: '20px',
                      borderRadius: '8px',
                      marginBottom: '20px'
                    }}>
                      <h3 style={{ color: '#856404', marginTop: 0 }}>📈 Process Stats</h3>
                      <div style={{ fontSize: '14px' }}>
                        <div style={{ marginBottom: '10px' }}>
                          <strong>Iterations:</strong> {currentState.iteration_count}
                        </div>
                        <div style={{ marginBottom: '10px' }}>
                          <strong>Drafts Created:</strong> {currentState.draft_history.length}
                        </div>
                        <div style={{ marginBottom: '10px' }}>
                          <strong>Original Intent:</strong>
                          <div style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
                            {currentState.user_intent}
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Agent Feedback */}
                    <div style={{
                      background: '#d4edda',
                      padding: '20px',
                      borderRadius: '8px'
                    }}>
                      <h3 style={{ color: '#155724', marginTop: 0 }}>🤖 Agent Feedback</h3>
                      {currentState.reviews.map((review: any, index: number) => (
                        <div key={index} style={{
                          marginBottom: '10px',
                          padding: '10px',
                          background: 'rgba(255,255,255,0.7)',
                          borderRadius: '4px'
                        }}>
                          <div style={{ 
                            fontSize: '12px', 
                            fontWeight: 'bold',
                            color: review.agent === 'SafetyGuardian' ? '#e74c3c' : '#3498db'
                          }}>
                            {review.agent}
                          </div>
                          <div style={{ fontSize: '12px' }}>
                            {review.notes}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div style={{
            background: 'white',
            borderRadius: '12px',
            padding: '30px',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
          }}>
            <h2 style={{ color: '#2c3e50', marginTop: 0 }}>📋 Generation History</h2>
            
            {tasks.length === 0 ? (
              <div style={{
                textAlign: 'center',
                padding: '40px',
                color: '#6c757d'
              }}>
                <div style={{ fontSize: '48px', marginBottom: '20px' }}>📭</div>
                <p>No generation tasks yet.</p>
                <p>Go to the Generator tab to create your first CBT exercise!</p>
              </div>
            ) : (
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
                gap: '20px'
              }}>
                {tasks.map((task: Task) => (
                  <div
                    key={task.thread_id}
                    style={{
                      border: '1px solid #dee2e6',
                      borderRadius: '8px',
                      padding: '15px',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      background: threadId === task.thread_id ? '#e8f4fc' : 'white'
                    }}
                    onClick={() => loadTask(task)}
                    onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                    onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                  >
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '10px'
                    }}>
                      <span style={{
                        padding: '2px 8px',
                        background: task.status === 'completed' ? '#d4edda' : 
                                   task.status === 'running' ? '#fff3cd' : 
                                   task.status === 'halted' ? '#cce5ff' : '#f8d7da',
                        color: task.status === 'completed' ? '#155724' : 
                               task.status === 'running' ? '#856404' : 
                               task.status === 'halted' ? '#004085' : '#721c24',
                        borderRadius: '12px',
                        fontSize: '12px',
                        fontWeight: 'bold'
                      }}>
                        {task.status.toUpperCase()}
                      </span>
                      <span style={{ fontSize: '12px', color: '#6c757d' }}>
                        {new Date(task.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    
                    <div style={{
                      fontSize: '14px',
                      marginBottom: '10px',
                      height: '60px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}>
                      {task.intent}
                    </div>
                    
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: '12px',
                      color: '#6c757d'
                    }}>
                      <span>Iterations: {task.iterations}</span>
                      <span>Click to load</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer style={{
        marginTop: '50px',
        paddingTop: '20px',
        borderTop: '1px solid #e0e0e0',
        textAlign: 'center',
        color: '#7f8c8d',
        fontSize: '14px'
      }}>
        <p>
          Cerina Protocol Foundry v2.0 | Multi-Agent CBT Exercise Generator
        </p>
        <p style={{ color: '#4a90e2', marginTop: '5px' }}>
          ⚠️ For educational purposes only. Not a substitute for professional medical advice.
        </p>
        <div style={{ marginTop: '10px', fontSize: '12px', color: '#adb5bd' }}>
          Backend: {API_URL} | {status !== 'idle' ? `Current: ${threadId}` : 'Ready'}
        </div>
      </footer>

      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

export default App;