
import React, { useState } from 'react';

const ResearchOnboarding = () => {
  const [tier, setTier] = useState(3); // Default to Tier 3 (Zero-Install)
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    ss_id: '',
    github_username: '',
    figshare_id: ''
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleInputChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...formData, tier }),
      });
      const data = await response.json();
      if (response.ok) {
        setResult(data);
      } else {
        alert(data.detail || 'Registration failed');
      }
    } catch (err) {
      alert('Connection error');
    }
    setLoading(false);
  };

  return (
    <div className="max-w-2xl mx-auto p-8 bg-gray-50 min-h-screen font-sans">
      <h1 className="text-3xl font-bold text-blue-900 mb-2">My Research Node</h1>
      <p className="text-gray-600 mb-8">Join the distributed web of science.</p>

      <div className="flex gap-4 mb-8">
        <button 
          onClick={() => setTier(3)}
          className={`px-4 py-2 rounded ${tier === 3 ? 'bg-blue-600 text-white' : 'bg-white border'}`}
        >
          Tier 3: Zero-Install
        </button>
        <button 
          onClick={() => setTier(2)}
          className={`px-4 py-2 rounded ${tier === 2 ? 'bg-blue-600 text-white' : 'bg-white border'}`}
        >
          Tier 2: Local Node
        </button>
      </div>

      {!result ? (
        <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-md space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Full Name</label>
            <input name="name" onChange={handleInputChange} className="w-full border p-2 rounded mt-1" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input name="email" type="email" onChange={handleInputChange} className="w-full border p-2 rounded mt-1" required />
          </div>

          <div className="border-t pt-4">
            <h3 className="font-semibold mb-2">Research IDs (Optional)</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <input name="ss_id" placeholder="Semantic Scholar ID" onChange={handleInputChange} className="border p-2 rounded" />
              <input name="github_username" placeholder="GitHub Username" onChange={handleInputChange} className="border p-2 rounded" />
              <input name="figshare_id" placeholder="Figshare ID" onChange={handleInputChange} className="border p-2 rounded" />
            </div>
          </div>

          <button type="submit" disabled={loading} className="w-full bg-blue-700 text-white py-3 rounded-lg font-bold hover:bg-blue-800 transition">
            {loading ? 'Processing...' : 'Generate My Research Agent'}
          </button>
        </form>
      ) : (
        <div className="bg-green-50 border border-green-200 p-6 rounded-lg">
          <h2 className="text-xl font-bold text-green-800 mb-4">Success! Your Node is Ready.</h2>
          <p className="mb-2">Your Slug: <code className="bg-white px-2 py-1 rounded">{result.slug}</code></p>

          {tier === 2 && (
            <div className="mt-4 p-4 bg-white rounded border">
              <p className="font-bold text-sm mb-2">Tier 2 Instructions:</p>
              <p className="text-sm text-gray-600">Download the <code>tier2_local_node.py</code> script and run it with your slug to connect your laptop to the network.</p>
            </div>
          )}

          <div className="mt-4">
            <p className="font-bold text-sm mb-2">Embed Widget Code:</p>
            <textarea 
              readOnly 
              className="w-full h-24 p-2 text-xs font-mono bg-gray-900 text-green-400 rounded"
              value={`<script src="https://your-hub.com/widget.js?slug=${result.slug}"></script>`}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default ResearchOnboarding;
