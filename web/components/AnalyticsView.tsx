import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { users, skillProgressionData, aiCoachingTips } from '../constants';
import { Skill } from '../types';

const AnalyticsView: React.FC = () => {
  const currentUser = users['user1'];
  const userSkills = currentUser.skills || [];
  const skillColors = ['#3b82f6', '#8b5cf6', '#10b981', '#ef4444', '#f97316'];

  const SkillCoachingCard: React.FC<{ skill: Skill }> = ({ skill }) => {
    const tips = aiCoachingTips[skill.id] || [];
    return (
      <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
        <h4 className="text-md font-bold text-white">{skill.name}</h4>
        <div className="flex items-center gap-4 my-3">
          <div className="relative w-full bg-gray-700 rounded-full h-2.5">
            <div className="bg-purple-accent h-2.5 rounded-full" style={{ width: `${skill.score}%` }}></div>
          </div>
          <span className="font-semibold text-white">{skill.score} <span className="text-sm text-gray-400">/ 100</span></span>
        </div>
        <div>
          <h5 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
             <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-purple-accent"><path d="M12 20.94c1.5 0 2.75 1.06 4 1.06 3 0 6-8 6-12.22A4.91 4.91 0 0 0 17 5c-2.22 0-4 1.44-4 4s1.78 4 4 4c0 2.22-1.78 4-4 4Z"/><path d="M4 12.22V18c0 1.21.57 2.26 1.5 3s2.29 1.06 3.5 1.06c.92 0 1.75-.29 2.5-.81"/><path d="M4 12.22C4 8 7 2 12 2c1.07 0 2.06.37 2.87 1.01"/></svg>
             AI Coaching Tips
          </h5>
          <ul className="list-disc list-inside space-y-2 text-sm text-gray-400">
            {tips.map((tip, index) => <li key={index}>{tip}</li>)}
          </ul>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-8">
      <h2 className="text-3xl font-bold text-white">My Personalized Analytics</h2>
      
      {userSkills.length > 0 ? (
        <>
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <h3 className="text-lg font-semibold text-white mb-4">My Skill Progression</h3>
                <ResponsiveContainer width="100%" height={400}>
                <LineChart data={skillProgressionData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="name" stroke="#9ca3af" />
                    <YAxis stroke="#9ca3af" />
                    <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }} />
                    <Legend wrapperStyle={{ color: '#9ca3af' }}/>
                    {userSkills.map((skill, index) => (
                        <Line key={skill.id} type="monotone" dataKey={skill.name} stroke={skillColors[index % skillColors.length]} strokeWidth={2} />
                    ))}
                </LineChart>
                </ResponsiveContainer>
            </div>
      
            <div>
                <h3 className="text-xl font-bold text-white mb-4">AI Coaching Dashboard</h3>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {userSkills.map(skill => <SkillCoachingCard key={skill.id} skill={skill} />)}
                </div>
            </div>
        </>
      ) : (
        <div className="bg-gray-800 p-8 rounded-xl border border-gray-700 text-center">
            <h3 className="text-xl font-semibold text-white">Define Your Role to Get Started</h3>
            <p className="text-gray-400 mt-2">Go to the Settings page to describe your role. Our AI will then create a personalized skill set for you to track and improve.</p>
        </div>
      )}
    </div>
  );
};

export default AnalyticsView;