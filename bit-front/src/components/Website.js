import React, { useState } from 'react';
import { API_BASE_URL, AGENT_ID } from '../config';

function Website() {
  const [companyName, setCompanyName] = useState('');
  const [companyUrl, setCompanyUrl] = useState('');
  const [isUpdating, setIsUpdating] = useState(false);
  const [updateMessage, setUpdateMessage] = useState({ text: '', isError: false });

  const handleUpdateCompanyInfo = async () => {
    setIsUpdating(true);
    setUpdateMessage({ text: '', isError: false });
    
    try {
      const response = await fetch(`${API_BASE_URL}/update_agent_vars`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          agent_id: AGENT_ID,
          company_name: companyName,
          company_url: companyUrl
        })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setUpdateMessage({ 
          text: '✨ Success! Your AI assistant is now configured. Your custom phone number is +1 (833) 573-5835!', 
          isError: false 
        });
      } else {
        setUpdateMessage({ 
          text: data.detail || 'Failed to update agent configuration', 
          isError: true 
        });
      }
    } catch (error) {
      setUpdateMessage({ 
        text: 'Network error: Could not connect to the server. Please check if the backend is running.', 
        isError: true 
      });
      console.error('Error updating agent configuration:', error);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && companyName && companyUrl && !isUpdating) {
      handleUpdateCompanyInfo();
    }
  };

  return (
    <div className="website-dashboard">
      {/* FLOATING PARTICLES */}
      <div className="particle-container">
        {[...Array(30)].map((_, i) => (
          <div 
            key={i} 
            className="particle-sleek"
            style={{
              left: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 10}s`,
              animationDuration: `${20 + Math.random() * 15}s`
            }}
          />
        ))}
      </div>
      
      {/* ANIMATED BACKGROUND GRADIENTS */}
      <div className="tech-grid"></div>
      
      {/* FLOATING SHAPES */}
      <div className="glow-orb orb-1"></div>
      <div className="glow-orb orb-2"></div>
      <div className="glow-orb orb-3"></div>
      
      <div className="dashboard-header">
        <h1 className="dashboard-title">Welcome</h1>
        <p className="dashboard-subtitle">Set up your AI assistant in seconds</p>
      </div>

      <div className="dashboard-grid">
        <div className="grid-item company-info">
          <div className="card-header">
            <h2 className="card-title">Company Setup</h2>
            <span className="card-badge">LIVE</span>
          </div>
          
          <div className="form-group">
            <label htmlFor="companyName">Company Name</label>
            <div className="input-group">
              <input 
                type="text" 
                id="companyName"
                placeholder="Enter your company name" 
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                onKeyPress={handleKeyPress}
                autoComplete="organization"
              />
            </div>
          </div>
          
          <div className="form-group">
            <label htmlFor="companyUrl">Website URL</label>
            <div className="input-group">
              <input 
                type="url" 
                id="companyUrl"
                placeholder="https://your-website.com" 
                value={companyUrl}
                onChange={(e) => setCompanyUrl(e.target.value)}
                onKeyPress={handleKeyPress}
                autoComplete="url"
              />
            </div>
          </div>
          
          <button 
            type="button" 
            className="modern-button primary full-width"
            onClick={handleUpdateCompanyInfo}
            disabled={isUpdating || !companyName || !companyUrl}
          >
            {isUpdating ? '✨ Setting Up...' : '🚀 Launch Assistant'}
          </button>
          
          {updateMessage.text && (
            <div className={`update-message ${updateMessage.isError ? 'error' : 'success'}`}>
              {updateMessage.text}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Website;
