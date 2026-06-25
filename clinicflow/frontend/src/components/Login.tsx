import React, { useState, useEffect } from 'react';
import { ShieldAlert, LogIn, Lock, User as UserIcon } from 'lucide-react';
import { login } from '../api/client';

interface Props {
  onLoginSuccess: (token: string, username: string) => void;
}

export default function Login({ onLoginSuccess }: Props) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lockoutSeconds, setLockoutSeconds] = useState(0);

  useEffect(() => {
    if (lockoutSeconds <= 0) return;
    const interval = setInterval(() => {
      setLockoutSeconds(prev => prev - 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [lockoutSeconds]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError('Username and password are required.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await login(username, password);
      onLoginSuccess(data.token, data.username);
    } catch (err: any) {
      const errMsg = err?.message || 'Login failed.';
      setError(errMsg);
      
      // Parse lockout seconds if present in error message
      // Details contain text like "Please wait {seconds}s"
      const match = errMsg.match(/wait\s+(\d+)s/i);
      if (match && match[1]) {
        setLockoutSeconds(parseInt(match[1], 10));
      } else if (errMsg.includes('Too many failed attempts')) {
        setLockoutSeconds(30);
      }
    } finally {
      setLoading(false);
    }
  };

  const isLockedOut = lockoutSeconds > 0;

  return (
    <div className="min-h-[80vh] flex items-center justify-center p-4">
      {/* 3D Elevated Login card */}
      <div 
        className="clinic-card-3d w-full max-w-md overflow-hidden"
        style={{ perspective: '1200px', transformStyle: 'preserve-3d' }}
      >
        <div className="p-8 space-y-6">
          <div className="text-center space-y-2">
            <div className="w-12 h-12 bg-gradient-to-tr from-teal-500 to-indigo-500 rounded-2xl flex items-center justify-center mx-auto shadow-lg shadow-teal-500/10 mb-2">
              <Lock className="w-5 h-5 text-white" />
            </div>
            <h2 className="text-xl font-bold tracking-tight text-slate-800">ClinicFlow Executive Portal</h2>
            <p className="text-xs text-slate-500">Sign in to access Receptionist Playground & logs</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg text-xs flex items-start gap-2 animate-fadeIn transition-all duration-300">
                <ShieldAlert className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Username</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <UserIcon className="w-4 h-4" />
                </div>
                <input
                  type="text"
                  disabled={loading || isLockedOut}
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  placeholder="Enter username"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white text-slate-800 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition-all"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Password</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type="password"
                  disabled={loading || isLockedOut}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Enter password"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white text-slate-800 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition-all"
                />
              </div>
            </div>

            {isLockedOut ? (
              <div className="p-4 bg-amber-50 border border-amber-200 text-amber-800 text-center rounded-lg text-xs font-semibold animate-pulse transition-all duration-300">
                Too many failed attempts. Please wait {lockoutSeconds}s.
              </div>
            ) : (
              <button
                type="submit"
                disabled={loading || !username.trim() || !password.trim()}
                className="w-full py-2.5 bg-gradient-to-r from-teal-600 to-sky-600 hover:from-teal-700 hover:to-sky-700 text-white rounded-lg text-xs font-bold shadow-md shadow-teal-500/10 flex items-center justify-center gap-1.5 transition-all btn-3d disabled:opacity-50 disabled:cursor-not-allowed mt-2"
              >
                <LogIn className="w-4 h-4" /> Sign In
              </button>
            )}
          </form>

          <div className="pt-2 text-center text-[10px] text-slate-400">
            For demonstration/testing use username: <span className="font-bold text-slate-500">admin</span> & password: <span className="font-bold text-slate-500">password123</span>
          </div>
        </div>
      </div>
    </div>
  );
}
