
import React from 'react';
import { Meeting } from '../types';

interface MeetingsViewProps {
  meetings: Meeting[];
  onSelectMeeting: (meeting: Meeting) => void;
}

const MeetingsView: React.FC<MeetingsViewProps> = ({ meetings, onSelectMeeting }) => {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-3xl font-bold text-white">Meetings</h2>
        <button className="bg-blue-accent text-white px-4 py-2 rounded-lg font-semibold hover:bg-blue-600 transition-colors">
          + New Meeting
        </button>
      </div>

      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-700">
          <thead className="bg-gray-700/50">
            <tr>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Title</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Date</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Duration</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Participants</th>
              <th scope="col" className="relative px-6 py-3"><span className="sr-only">View</span></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {meetings.map(meeting => (
              <tr key={meeting.id} className="hover:bg-gray-700/50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-white">{meeting.title}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-400">{new Date(meeting.date).toLocaleString()}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-400">{meeting.duration} mins</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex -space-x-2 overflow-hidden">
                    {meeting.participants.map(p => (
                      <img key={p.id} className="inline-block h-8 w-8 rounded-full ring-2 ring-gray-800" src={p.avatarUrl} alt={p.name} />
                    ))}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button onClick={() => onSelectMeeting(meeting)} className="text-blue-accent hover:text-blue-500">
                    View Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default MeetingsView;
