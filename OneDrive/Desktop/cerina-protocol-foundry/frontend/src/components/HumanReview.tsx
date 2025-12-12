// frontend/src/components/HumanReview.tsx
// frontend/src/components/HumanReview.tsx
import React, { useState } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { GraphState } from '../types';

const API_URL = 'http://localhost:8000';

interface HumanReviewProps {
    threadId: string;
    state: GraphState;
    onComplete: () => void;
    onResuming: () => void;
}

const HumanReview: React.FC<HumanReviewProps> = ({ threadId, state, onComplete, onResuming }) => {
    const [editedDraft, setEditedDraft] = useState(state.draft);
    const [feedback, setFeedback] = useState('');
    const [isProcessing, setIsProcessing] = useState(false);
    const [activeTab, setActiveTab] = useState<'edit' | 'preview'>('edit');

    const handleApprove = async () => {
        setIsProcessing(true);
        onResuming();
        
        try {
            const payload = {
                approved: true,
                feedback: feedback || "Approved without additional feedback"
            };
            
            // If draft was edited, include it
            if (editedDraft !== state.draft) {
                (payload as any).edited_draft = editedDraft;
            }
            
            await axios.post(`${API_URL}/resume/${threadId}`, payload);
            
            // Parent will handle polling for completion
        } catch (error: any) {
            console.error("Error approving:", error);
            alert(`Error approving draft: ${error.response?.data?.message || error.message}`);
            setIsProcessing(false);
        }
    };

    const handleReject = async () => {
        setIsProcessing(true);
        
        try {
            await axios.post(`${API_URL}/resume/${threadId}`, {
                approved: false,
                feedback: feedback || "Rejected without specific feedback"
            });
            
            alert("Draft rejected. Process stopped.");
            onComplete();
        } catch (error: any) {
            console.error("Error rejecting:", error);
            alert(`Error rejecting draft: ${error.response?.data?.message || error.message}`);
            setIsProcessing(false);
        }
    };

    const copyToClipboard = () => {
        navigator.clipboard.writeText(editedDraft);
        alert("Draft copied to clipboard!");
    };

    const downloadAsMarkdown = () => {
        const blob = new Blob([editedDraft], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `cbt_exercise_${new Date().toISOString().slice(0, 10)}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    return (
        <div style={{
            border: '2px solid #4a90e2',
            borderRadius: '12px',
            padding: '24px',
            marginTop: '20px',
            background: '#f8f9fa'
        }}>
            <h2 style={{ color: '#2c3e50', marginBottom: '20px' }}>
                👤 Human Review Required
            </h2>
            
            {/* Status Summary */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '20px',
                marginBottom: '20px'
            }}>
                <div style={{
                    background: '#e8f4fc',
                    padding: '15px',
                    borderRadius: '8px'
                }}>
                    <h3 style={{ color: '#2980b9', marginTop: 0, fontSize: '14px' }}>📊 Scores</h3>
                    <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
                        <div>
                            <div style={{ fontSize: '12px', color: '#666' }}>Safety</div>
                            <div style={{
                                fontSize: '24px',
                                fontWeight: 'bold',
                                color: state.scores.safety >= 8 ? '#27ae60' : 
                                       state.scores.safety >= 6 ? '#f39c12' : '#e74c3c'
                            }}>
                                {state.scores.safety}/10
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: '12px', color: '#666' }}>Clinical</div>
                            <div style={{
                                fontSize: '24px',
                                fontWeight: 'bold',
                                color: state.scores.clinical >= 8 ? '#27ae60' : 
                                       state.scores.clinical >= 6 ? '#f39c12' : '#e74c3c'
                            }}>
                                {state.scores.clinical}/10
                            </div>
                        </div>
                    </div>
                </div>
                
                <div style={{
                    background: '#fff3cd',
                    padding: '15px',
                    borderRadius: '8px'
                }}>
                    <h3 style={{ color: '#856404', marginTop: 0, fontSize: '14px' }}>🔄 Process</h3>
                    <div style={{ fontSize: '14px' }}>
                        <div><strong>Iteration:</strong> {state.iteration_count}</div>
                        <div><strong>Drafts:</strong> {state.draft_history.length}</div>
                        <div><strong>Status:</strong> Awaiting review</div>
                    </div>
                </div>
                
                <div style={{
                    background: '#d4edda',
                    padding: '15px',
                    borderRadius: '8px'
                }}>
                    <h3 style={{ color: '#155724', marginTop: 0, fontSize: '14px' }}>🎯 Intent</h3>
                    <div style={{ fontSize: '14px', wordBreak: 'break-word' }}>
                        {state.user_intent}
                    </div>
                </div>
            </div>
            
            {/* Reviewer Notes */}
            <div style={{
                background: '#fff',
                border: '1px solid #dee2e6',
                borderRadius: '8px',
                padding: '15px',
                marginBottom: '20px'
            }}>
                <details>
                    <summary style={{ cursor: 'pointer', color: '#495057', fontWeight: 'bold' }}>
                        📝 View Reviewer Notes & Reasoning
                    </summary>
                    <div style={{ marginTop: '15px' }}>
                        {state.reviews.map((review: any, index: number) => (
                            <div key={index} style={{
                                marginBottom: '15px',
                                padding: '10px',
                                background: index % 2 === 0 ? '#f8f9fa' : 'white',
                                borderRadius: '6px'
                            }}>
                                <div style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    marginBottom: '5px'
                                }}>
                                    <strong style={{
                                        color: review.agent === 'SafetyGuardian' ? '#e74c3c' : '#3498db'
                                    }}>
                                        {review.agent}
                                    </strong>
                                    <span style={{
                                        padding: '2px 8px',
                                        background: review.score >= 8 ? '#d4edda' : 
                                                   review.score >= 6 ? '#fff3cd' : '#f8d7da',
                                        color: review.score >= 8 ? '#155724' : 
                                               review.score >= 6 ? '#856404' : '#721c24',
                                        borderRadius: '12px',
                                        fontSize: '12px'
                                    }}>
                                        Score: {review.score}/10
                                    </span>
                                </div>
                                <div style={{ margin: '5px 0', fontSize: '14px' }}>
                                    {review.notes}
                                </div>
                                <div style={{
                                    fontSize: '12px',
                                    color: '#6c757d',
                                    fontStyle: 'italic',
                                    marginTop: '5px',
                                    paddingLeft: '10px',
                                    borderLeft: '2px solid #dee2e6'
                                }}>
                                    <strong>Reasoning:</strong> {review.reasoning}
                                </div>
                            </div>
                        ))}
                    </div>
                </details>
            </div>
            
            {/* Draft Editor/Preview */}
            <div style={{ marginBottom: '20px' }}>
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '10px'
                }}>
                    <div>
                        <h3 style={{ color: '#2c3e50', margin: 0 }}>✏️ Draft</h3>
                        <div style={{ fontSize: '12px', color: '#6c757d' }}>
                            Edit the draft below or review as-is
                        </div>
                    </div>
                    
                    <div style={{ display: 'flex', gap: '10px' }}>
                        <button
                            onClick={() => setActiveTab('edit')}
                            style={{
                                padding: '5px 15px',
                                background: activeTab === 'edit' ? '#4a90e2' : '#f8f9fa',
                                color: activeTab === 'edit' ? 'white' : '#495057',
                                border: '1px solid #dee2e6',
                                borderRadius: '4px',
                                cursor: 'pointer'
                            }}
                        >
                            Edit
                        </button>
                        <button
                            onClick={() => setActiveTab('preview')}
                            style={{
                                padding: '5px 15px',
                                background: activeTab === 'preview' ? '#4a90e2' : '#f8f9fa',
                                color: activeTab === 'preview' ? 'white' : '#495057',
                                border: '1px solid #dee2e6',
                                borderRadius: '4px',
                                cursor: 'pointer'
                            }}
                        >
                            Preview
                        </button>
                        <button
                            onClick={copyToClipboard}
                            style={{
                                padding: '5px 15px',
                                background: '#6c757d',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer'
                            }}
                        >
                            📋 Copy
                        </button>
                        <button
                            onClick={downloadAsMarkdown}
                            style={{
                                padding: '5px 15px',
                                background: '#28a745',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer'
                            }}
                        >
                            💾 Save
                        </button>
                    </div>
                </div>
                
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: activeTab === 'edit' ? '1fr' : '1fr',
                    gap: '20px',
                    height: '400px'
                }}>
                    {activeTab === 'edit' ? (
                        <textarea
                            value={editedDraft}
                            onChange={(e) => setEditedDraft(e.target.value)}
                            style={{
                                width: '100%',
                                height: '100%',
                                padding: '15px',
                                fontFamily: "'Courier New', monospace",
                                fontSize: '14px',
                                border: '1px solid #ddd',
                                borderRadius: '8px',
                                resize: 'none',
                                lineHeight: '1.5'
                            }}
                        />
                    ) : (
                        <div style={{
                            padding: '15px',
                            border: '1px solid #ddd',
                            borderRadius: '8px',
                            background: 'white',
                            overflowY: 'auto',
                            height: '100%'
                        }}>
                            <ReactMarkdown>{editedDraft}</ReactMarkdown>
                        </div>
                    )}
                </div>
                
                {/* Draft History */}
                {state.draft_history.length > 1 && (
                    <div style={{ marginTop: '10px' }}>
                        <details>
                            <summary style={{ cursor: 'pointer', fontSize: '14px', color: '#495057' }}>
                                📚 View Draft History ({state.draft_history.length} versions)
                            </summary>
                            <div style={{ 
                                display: 'flex', 
                                gap: '10px', 
                                overflowX: 'auto', 
                                padding: '10px 0',
                                marginTop: '10px'
                            }}>
                                {state.draft_history.map((draft: string, index: number) => (
                                    <button
                                        key={index}
                                        onClick={() => setEditedDraft(draft)}
                                        style={{
                                            padding: '8px 12px',
                                            background: editedDraft === draft ? '#4a90e2' : '#f8f9fa',
                                            color: editedDraft === draft ? 'white' : '#495057',
                                            border: '1px solid #dee2e6',
                                            borderRadius: '4px',
                                            cursor: 'pointer',
                                            whiteSpace: 'nowrap',
                                            fontSize: '12px'
                                        }}
                                    >
                                        Draft {index + 1}
                                    </button>
                                ))}
                            </div>
                        </details>
                    </div>
                )}
            </div>
            
            {/* Feedback Section */}
            <div style={{ marginBottom: '20px' }}>
                <h3 style={{ color: '#2c3e50', marginBottom: '10px' }}>💬 Your Feedback (Optional)</h3>
                <textarea
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    placeholder="Add any feedback or notes for the AI system..."
                    style={{
                        width: '100%',
                        height: '80px',
                        padding: '10px',
                        border: '1px solid #ddd',
                        borderRadius: '6px',
                        resize: 'vertical',
                        fontSize: '14px'
                    }}
                />
                <div style={{ fontSize: '12px', color: '#6c757d', marginTop: '5px' }}>
                    This feedback will be recorded with your decision.
                </div>
            </div>
            
            {/* Action Buttons */}
            <div style={{
                display: 'flex',
                gap: '15px',
                justifyContent: 'center',
                marginTop: '20px'
            }}>
                <button
                    onClick={handleApprove}
                    disabled={isProcessing}
                    style={{
                        padding: '12px 30px',
                        background: '#28a745',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '16px',
                        fontWeight: 'bold',
                        cursor: isProcessing ? 'not-allowed' : 'pointer',
                        opacity: isProcessing ? 0.7 : 1,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
                    }}
                >
                    {isProcessing ? (
                        <>
                            <span style={{ animation: 'spin 1s linear infinite' }}>⟳</span>
                            Processing...
                        </>
                    ) : (
                        <>
                            ✅ Approve & Finalize
                        </>
                    )}
                </button>
                
                <button
                    onClick={handleReject}
                    disabled={isProcessing}
                    style={{
                        padding: '12px 30px',
                        background: '#dc3545',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        fontSize: '16px',
                        cursor: isProcessing ? 'not-allowed' : 'pointer',
                        opacity: isProcessing ? 0.7 : 1,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
                    }}
                >
                    ❌ Reject Draft
                </button>
            </div>
            
            <style>{`
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
};

export default HumanReview;