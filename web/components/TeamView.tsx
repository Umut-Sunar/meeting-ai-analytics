
import React from 'react';
import { users } from '../constants';

const teamMembers = Object.values(users).filter(u => u.id !== 'user1'); // Everyone except the manager

const teamData = teamMembers.map(member => ({
  ...member,
  meetings: Math.floor(Math.random() * 20) + 5,
  talkRatio: `${Math.floor(Math.random() * 20) + 40}%`,
  topSkill: ['Closing', 'Discovery', 'Negotiation'][Math.floor(Math.random() * 3)],
}));

const TeamView: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-3xl font-bold text-white">Team Performance</h2>
        <button className="bg-blue-accent text-white px-4 py-2 rounded-lg font-semibold hover:bg-blue-600 transition-colors">
          + Invite Member
        </button>
      </div>
      
      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-700">
          <thead className="bg-gray-700/50">
            <tr>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Member</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Role</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Meetings (Month)</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Avg. Talk Ratio</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Top Skill</th>
              <th scope="col" className="relative px-6 py-3"><span className="sr-only">Details</span></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {teamData.map(member => (
              <tr key={member.id} className="hover:bg-gray-700/50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="flex-shrink-0 h-10 w-10">
                      <img className="h-10 w-10 rounded-full" src={member.avatarUrl} alt={member.name} />
                    </div>
                    <div className="ml-4">
                      <div className="text-sm font-medium text-white">{member.name}</div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-900 text-green-300">{member.role}</span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{member.meetings}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{member.talkRatio}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{member.topSkill}</td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <a href="#" className="text-blue-accent hover:text-blue-500">View Analytics</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TeamView;
