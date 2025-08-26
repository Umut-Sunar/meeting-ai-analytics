import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { meetings, overallPerformanceData } from '../constants';
import { Meeting } from '../types';

interface DashboardViewProps {
  onSelectMeeting: (meeting: Meeting) => void;
}

const talkRatioData = [
    { name: 'Q1', me: 40, others: 60 },
    { name: 'Q2', me: 45, others: 55 },
    { name: 'Q3', me: 55, others: 45 },
    { name: 'Q4', me: 50, others: 50 },
];

const Card: React.FC<{ title: string; value: string; change?: string; changeType?: 'increase' | 'decrease' }> = ({ title, value, change, changeType }) => (
  <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
    <h3 className="text-sm font-medium text-gray-400">{title}</h3>
    <p className="text-3xl font-bold text-white mt-2">{value}</p>
    {change && (
      <p className={`text-xs mt-2 flex items-center ${changeType === 'increase' ? 'text-green-400' : 'text-red-400'}`}>
        {changeType === 'increase' ? '▲' : '▼'} {change} vs last month
      </p>
    )}
  </div>
);

const DashboardView: React.FC<DashboardViewProps> = ({ onSelectMeeting }) => {
  return (
    <div className="space-y-8">
      <h2 className="text-3xl font-bold text-white">Dashboard</h2>

      {/* Remaining Meeting Credits Banner */}
      <div className="bg-gray-800 p-4 rounded-xl border border-purple-accent/30 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6 text-purple-accent mr-3"><path d="M12 2v4"/><path d="m16.2 7.8 2.9-2.9"/><path d="M18 12h4"/><path d="m16.2 16.2 2.9 2.9"/><path d="M12 18v4"/><path d="m7.8 16.2-2.9 2.9"/><path d="M6 12H2"/><path d="m7.8 7.8-2.9-2.9"/><circle cx="12" cy="12" r="4"/></svg>
            <div>
                <h3 className="font-semibold text-white">Remaining Meeting Credits</h3>
                <p className="text-sm text-gray-400">240 / 800 minutes used this month</p>
            </div>
        </div>
        <div className="flex items-center space-x-4">
            <div className="w-40 sm:w-48 bg-gray-700 rounded-full h-2.5">
                <div className="bg-purple-accent h-2.5 rounded-full" style={{ width: '30%' }}></div>
            </div>
            <button className="bg-purple-accent text-white px-4 py-2 rounded-lg font-semibold hover:bg-purple-600 transition-colors text-sm shrink-0">
                Upgrade Plan
            </button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card title="Meetings This Month" value="12" change="+20%" changeType="increase" />
        <Card title="Avg. Talk Ratio" value="48%" change="-5%" changeType="decrease" />
        <Card title="Top Skill" value="Closing" change="+8%" changeType="increase" />
        <Card title="Action Items" value="23" change="+15%" changeType="increase" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Overall Performance Trend</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={overallPerformanceData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="name" stroke="#9ca3af" />
              <YAxis domain={[50, 80]} stroke="#9ca3af" />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }} />
              <Line type="monotone" dataKey="score" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4, fill: '#3b82f6' }} activeDot={{ r: 8 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Talk Ratio Trend (Me vs. Others)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={talkRatioData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="name" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }} />
              <Bar dataKey="me" stackId="a" fill="#3b82f6" name="Me" />
              <Bar dataKey="others" stackId="a" fill="#8b5cf6" name="Others" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      
      <div>
        <h3 className="text-xl font-bold text-white mb-4">Recent Meetings</h3>
        <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
          <ul className="divide-y divide-gray-700">
            {meetings.slice(0, 3).map(meeting => (
              <li key={meeting.id} className="p-4 hover:bg-gray-700 transition-colors cursor-pointer" onClick={() => onSelectMeeting(meeting)}>
                <div className="flex justify-between items-center">
                  <div>
                    <p className="font-semibold text-white">{meeting.title}</p>
                    <p className="text-sm text-gray-400">{new Date(meeting.date).toLocaleDateString()} - {meeting.duration} mins</p>
                  </div>
                  <div className="flex -space-x-2">
                    {meeting.participants.map(p => <img key={p.id} src={p.avatarUrl} alt={p.name} className="w-8 h-8 rounded-full border-2 border-gray-800"/>)}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};

export default DashboardView;