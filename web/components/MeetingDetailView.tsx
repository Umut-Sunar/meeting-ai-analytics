import React, { useState } from 'react';
import { Meeting, TranscriptSegment } from '../types';
import { aiPrompts } from '../constants';

interface MeetingDetailViewProps {
  meeting: Meeting;
  onBack: () => void;
}

const TranscriptItem: React.FC<{ segment: TranscriptSegment, participant: any }> = ({ segment, participant }) => {
    const getInitials = (name:string) => name.split(' ').map(n => n[0]).join('');
    const speakerInitial = getInitials(participant?.name || '??');
    const colors = ['bg-green-500', 'bg-yellow-500', 'bg-indigo-500', 'bg-pink-500', 'bg-sky-500'];
    const color = colors[participant?.name.length % colors.length || 0];

    return (
        <div className="flex items-start gap-4 py-3">
             <div className={`w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center text-white font-bold text-sm ${color}`}>
                 {speakerInitial}
             </div>
            <div className="flex flex-col">
                <div className="flex items-baseline gap-2">
                     <span className="font-bold text-sm text-white">{segment.speakerLabel}</span>
                    <button className="text-xs text-blue-accent hover:underline">
                        {new Date(segment.timestamp * 1000).toISOString().substr(14, 5)}
                    </button>
                </div>
                <p className="text-sm text-gray-300 mt-1">{segment.text}</p>
            </div>
        </div>
    );
}

const AudioPlayer: React.FC<{ duration: number }> = ({ duration }) => {
    const formatTime = (minutes: number) => {
        const totalSeconds = minutes * 60;
        const mins = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
        const secs = (totalSeconds % 60).toString().padStart(2, '0');
        return `${mins}:${secs}`;
    };

    return (
        <div className="bg-gray-800 p-3 rounded-xl border border-gray-700 flex items-center space-x-4 mb-6">
            <button className="p-2 bg-blue-accent text-white rounded-full hover:bg-blue-600 transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" strokeWidth="0"><path d="M8 5v14l11-7z"/></svg>
            </button>
            <span className="text-sm font-mono text-gray-400">01:23</span>
            <div className="flex-1 bg-gray-600 h-1.5 rounded-full relative">
                <div className="absolute top-0 left-0 h-full bg-blue-accent rounded-full" style={{ width: '25%' }}></div>
                <div className="absolute top-1/2 -translate-y-1/2 bg-white w-3 h-3 rounded-full" style={{ left: '25%' }}></div>
            </div>
            <span className="text-sm font-mono text-gray-400">{formatTime(duration)}</span>
            <button className="text-sm font-semibold text-gray-300 hover:text-white bg-gray-700 px-3 py-1 rounded-md">1x</button>
             <button className="text-gray-400 hover:text-white">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>
            </button>
        </div>
    )
}

const DownloadMenu: React.FC = () => (
    <div className="absolute z-10 top-full w-64 bg-gray-700 border border-gray-600 rounded-lg shadow-xl pt-2 animate-fade-in-fast">
        <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase">Export</div>
        <a href="#" className="flex items-center px-3 py-2 text-sm text-gray-300 hover:bg-gray-600 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-3"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>
            Download Audio (MP3)
        </a>
        <div className="border-t border-gray-600 my-1"></div>
        <div className="px-3 pt-2 pb-1 text-sm font-semibold text-gray-200">Download Transcript</div>
        <a href="#" className="flex items-center px-3 py-2 text-sm text-gray-300 hover:bg-gray-600 transition-colors">
             <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-3"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><path d="M10 12v-1a2 2 0 0 1 2-2 2 2 0 0 1 2 2v1"/><path d="M10 18h4"/><path d="M12 10v8"/></svg>
            As PDF (.pdf)
        </a>
        <a href="#" className="flex items-center px-3 py-2 text-sm text-gray-300 hover:bg-gray-600 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-3"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><path d="M12 18v-7a2 2 0 0 1 2-2 2 2 0 0 1 2 2v7"/><path d="M10 18h8"/></svg>
            As DOCX (.docx)
        </a>
        <a href="#" className="flex items-center px-3 py-2 text-sm text-gray-300 hover:bg-gray-600 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-3"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" x2="8" y1="13" y2="13"/><line x1="16" x2="8" y1="17" y2="17"/><line x1="10" x2="8" y1="9" y2="9"/></svg>
            As Text (.txt)
        </a>
    </div>
);


const MeetingDetailView: React.FC<MeetingDetailViewProps> = ({ meeting, onBack }) => {
  const summaryPrompts = aiPrompts.filter(p => p.tags?.includes('Meeting Summary'));

  const [activeTab, setActiveTab] = useState<'Transcript' | 'AskAI'>('Transcript');
  const [selectedPromptId, setSelectedPromptId] = useState<string>(summaryPrompts[0]?.id || aiPrompts[0].id);
  const [showDownloadMenu, setShowDownloadMenu] = useState(false);
  
  const currentSummary = meeting.summaries[selectedPromptId] || meeting.summaries[aiPrompts[0].id];

  const getParticipant = (speakerId: string) => meeting.participants.find(p => p.id === speakerId);

  return (
    <div className="max-w-7xl mx-auto">
        <button onClick={onBack} className="flex items-center text-sm text-blue-accent hover:underline mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4 mr-1"><path d="m15 18-6-6 6-6"/></svg>
            Back to Meetings
        </button>

      {/* Header */}
      <div className="mb-6">
        <div 
            className="relative inline-block"
            onMouseEnter={() => setShowDownloadMenu(true)}
            onMouseLeave={() => setShowDownloadMenu(false)}
        >
            <h1 className="text-3xl font-bold text-white flex items-center cursor-pointer group">
                {meeting.title}
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 ml-2 text-gray-500 group-hover:text-white transition-colors"><polyline points="6 9 12 15 18 9"/></svg>
            </h1>
            {showDownloadMenu && <DownloadMenu />}
        </div>
        <div className="flex items-center text-sm text-gray-400 mt-2 space-x-4">
            <div className="flex items-center">
                 <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
                 <span>{meeting.participants.map(p => p.name).join(', ')}</span>
            </div>
            <span>&bull;</span>
            <span>{new Date(meeting.date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
        </div>
      </div>

      {/* Audio Player */}
      <AudioPlayer duration={meeting.duration} />

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        {/* Left Column: AI Summaries */}
        <div className="lg:col-span-3 space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-purple-accent"><path d="M12 20.94c1.5 0 2.75 1.06 4 1.06 3 0 6-8 6-12.22A4.91 4.91 0 0 0 17 5c-2.22 0-4 1.44-4 4s1.78 4 4 4c0 2.22-1.78 4-4 4Z"/><path d="M4 12.22V18c0 1.21.57 2.26 1.5 3s2.29 1.06 3.5 1.06c.92 0 1.75-.29 2.5-.81"/><path d="M4 12.22C4 8 7 2 12 2c1.07 0 2.06.37 2.87 1.01"/></svg>
                    <h2 className="text-lg font-semibold text-white">AI Generated Summary</h2>
                </div>
                 <select 
                    value={selectedPromptId}
                    onChange={(e) => setSelectedPromptId(e.target.value)}
                    className="bg-gray-700 border border-gray-600 rounded-md px-3 py-1.5 text-sm text-white focus:ring-blue-accent focus:border-blue-accent">
                    {summaryPrompts.map(prompt => (
                        <option key={prompt.id} value={prompt.id}>{prompt.name}</option>
                    ))}
                </select>
            </div>
           
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <h3 className="text-md font-semibold text-white mb-3">Key Topics</h3>
                <div className="flex flex-wrap gap-2">
                    {currentSummary.keyTopics.map((topic, i) => (
                        <span key={i} className="bg-gray-700 text-gray-300 text-xs font-medium px-2.5 py-1 rounded-full">{topic}</span>
                    ))}
                </div>

                <h3 className="text-md font-semibold text-white mt-6 mb-3">Overview</h3>
                <ul className="list-disc list-inside space-y-2 text-sm text-gray-300">
                    {currentSummary.overview.map((item, i) => <li key={i}>{item}</li>)}
                </ul>

                <h3 className="text-md font-semibold text-white mt-6 mb-3">Action Items</h3>
                <ul className="list-disc list-inside space-y-2 text-sm text-gray-300">
                    {currentSummary.actionItems.map((item, i) => <li key={i}>{item}</li>)}
                </ul>
            </div>
             <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <h3 className="text-md font-semibold text-white mb-3">Notes</h3>
                 <textarea 
                    className="w-full h-24 bg-gray-700/50 text-gray-300 rounded-md p-2 border border-gray-600 focus:ring-2 focus:ring-blue-accent focus:border-transparent resize-none"
                    placeholder="Add personal notes here..."
                />
            </div>
        </div>

        {/* Right Column: Transcript */}
        <div className="lg:col-span-2 bg-gray-800 rounded-xl border border-gray-700 h-full max-h-[80vh] flex flex-col">
            <div className="flex border-b border-gray-700 flex-shrink-0">
                <button onClick={() => setActiveTab('Transcript')} className={`flex-1 px-4 py-3 text-sm font-semibold transition-colors ${activeTab === 'Transcript' ? 'border-b-2 border-blue-accent text-white' : 'text-gray-400 hover:text-white'}`}>Transcript</button>
                <button onClick={() => setActiveTab('AskAI')} className={`flex-1 px-4 py-3 text-sm font-semibold transition-colors ${activeTab === 'AskAI' ? 'border-b-2 border-blue-accent text-white' : 'text-gray-400 hover:text-white'}`}>Ask AI</button>
            </div>
            
            {activeTab === 'Transcript' && (
                <div className="p-4 flex-1 overflow-y-auto">
                    <div className="divide-y divide-gray-700">
                        {meeting.transcript.map((segment, index) => <TranscriptItem key={index} segment={segment} participant={getParticipant(segment.speaker)} />)}
                    </div>
                </div>
            )}
             {activeTab === 'AskAI' && (
                <div className="p-4 flex-1 flex flex-col items-center justify-center text-center">
                    <div className="bg-purple-accent/20 p-3 rounded-full mb-3">
                       <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-purple-accent"><path d="M15 4.13a8 8 0 0 1 0 15.74"/><path d="M9 20.13a8 8 0 0 1 0-15.74"/><path d="M12 2v20"/><path d="M22 12H2"/></svg>
                    </div>
                    <h3 className="font-semibold text-white">Ask AI Anything</h3>
                    <p className="text-sm text-gray-400 mt-1">Ask questions about this meeting, get clarifications, or generate content.</p>
                </div>
            )}
        </div>
      </div>
    </div>
  );
};

export default MeetingDetailView;