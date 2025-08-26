import React, { useState } from 'react';
import { aiPrompts, users } from '../constants';

const aiCues = [
    { icon: '💡', text: 'Good time to ask about their budget constraints.' },
    { icon: '📊', text: 'Mention the 20% performance improvement shown in the Q2 report.' },
    { icon: '❓', text: 'Clarify the project timeline for the integration phase.' },
    { icon: '🤝', text: 'They mentioned "scalability". Reassure them with our enterprise-grade infrastructure.' },
];

const liveTranscript = [
    { speaker: 'Them', text: "So, we're looking at the projections for next quarter, and the main concern is scalability.", translation: "Yani, gelecek çeyreğin projeksiyonlarına bakıyoruz ve asıl endişemiz ölçeklenebilirlik." },
    { speaker: 'You', text: "That makes sense. Our enterprise-grade infrastructure is designed for high-demand scenarios. We've seen a 20% performance improvement for clients of your scale.", translation: "Bu mantıklı. Kurumsal düzeydeki altyapımız, yüksek talep senaryoları için tasarlanmıştır. Sizin ölçeğinizdeki müşteriler için %20'lik bir performans artışı gördük." },
    { speaker: 'Them', text: "That's impressive. What about the integration phase? What does the timeline look like for that?", translation: "Bu etkileyici. Peki entegrasyon aşaması ne olacak? Bunun için zaman çizelgesi nasıl görünüyor?" },
    { speaker: 'You', text: "Great question. Typically, we can get you fully integrated within 4-6 weeks, depending on your team's availability.", translation: "Harika bir soru. Genellikle, ekibinizin müsaitliğine bağlı olarak sizi 4-6 hafta içinde tam olarak entegre edebiliriz." },
    { speaker: 'Them', text: "Okay, that fits within our schedule. The final piece of the puzzle is the budget.", translation: "Tamam, bu bizim programımıza uyuyor. Bulmacanın son parçası ise bütçe." },
];

const suggestedReplies = [
    "What budget range are you targeting for this initiative?",
    "We have flexible pricing models that can align with your budget.",
    "Let's discuss the value and ROI first, then we can align on a budget that works for both of us."
];

const initialChatHistory = [
    { sender: 'user', text: 'What were the main concerns from our last meeting with Acme?' },
    { sender: 'ai', text: 'In the last meeting, Acme Corp\'s main concerns were: 1. Scalability of the backend, 2. The timeline for integration, and 3. The total cost and ROI.' }
];

interface DummyFile {
    name: string;
    size: string;
}

const languages = [
    { code: 'en-US', name: 'English (US)' },
    { code: 'en-GB', name: 'English (UK)' },
    { code: 'es-ES', name: 'Spanish' },
    { code: 'fr-FR', name: 'French' },
    { code: 'de-DE', name: 'German' },
    { code: 'it-IT', name: 'Italian' },
    { code: 'pt-BR', name: 'Portuguese' },
    { code: 'tr-TR', name: 'Turkish' },
    { code: 'ja-JP', name: 'Japanese' },
    { code: 'ko-KR', name: 'Korean' },
];

const LiveTranscriptItem: React.FC<{item: {speaker: string, text: string, translation?: string}, showTranslation: boolean}> = ({item, showTranslation}) => {
    const isYou = item.speaker === 'You';
    return (
        <div className={`flex items-start gap-3 ${isYou ? 'flex-row-reverse' : ''}`}>
             {!isYou && <img src="https://picsum.photos/seed/other/40/40" className="w-8 h-8 rounded-full mt-1" />}
            <div className={`max-w-xs md:max-w-md p-3 rounded-xl ${isYou ? 'bg-blue-accent text-white' : 'bg-gray-700 text-gray-300'}`}>
                <p className="text-sm">{item.text}</p>
                {showTranslation && item.translation && (
                    <p className="text-xs text-gray-400 italic mt-2 pt-2 border-t border-gray-500/50">{item.translation}</p>
                )}
            </div>
             {isYou && <img src="https://picsum.photos/seed/alex/40/40" className="w-8 h-8 rounded-full mt-1" />}
        </div>
    )
}

const Toggle: React.FC<{ isEnabled: boolean; onToggle: () => void; label: string }> = ({ isEnabled, onToggle, label }) => (
    <div className="flex items-center space-x-2">
        <span className={`text-xs font-medium ${isEnabled ? 'text-white' : 'text-gray-400'}`}>{label}</span>
        <button
            onClick={onToggle}
            className={`relative inline-flex items-center h-6 rounded-full w-11 transition-colors ${isEnabled ? 'bg-blue-accent' : 'bg-gray-600'}`}
        >
            <span
                className={`inline-block w-4 h-4 transform bg-white rounded-full transition-transform ${isEnabled ? 'translate-x-6' : 'translate-x-1'}`}
            />
        </button>
    </div>
);


const DesktopAppView: React.FC = () => {
    const assistantPrompts = aiPrompts.filter(p => p.tags?.includes('Meeting Assistant'));
    
    const [meetingState, setMeetingState] = useState<'pre-meeting' | 'in-meeting'>('pre-meeting');
    const [meetingName, setMeetingName] = useState('Acme Corp. Client Pitch');
    const [uploadedFiles, setUploadedFiles] = useState<DummyFile[]>([]);
    const [selectedAssistantPrompt, setSelectedAssistantPrompt] = useState(assistantPrompts[0]?.id || '');
    const [selectedLanguage, setSelectedLanguage] = useState('en-US');
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    
    const [isSuperModeOn, setIsSuperModeOn] = useState(false);
    const [showTranslation, setShowTranslation] = useState(false);
    const [activeTab, setActiveTab] = useState<'cues' | 'chat'>('cues');
    const [chatHistory, setChatHistory] = useState(initialChatHistory);
    const [userInput, setUserInput] = useState('');
    const [meetingLanguage, setMeetingLanguage] = useState('English (US)');

    const currentUser = users['user1'];

    const handleSendMessage = () => {
        if (userInput.trim() === '') return;
        const newHistory = [...chatHistory, { sender: 'user' as const, text: userInput }];
        newHistory.push({ sender: 'ai' as const, text: "This is a simulated response based on your query. I can pull up documents, summarize past conversations, or find key data points." });
        setChatHistory(newHistory);
        setUserInput('');
    };
    
    const handleAddFile = () => {
        const dummyFiles = [
            { name: 'Project_Phoenix_PRD.pdf', size: '1.2MB' },
            { name: 'Q3_Marketing_Strategy.docx', size: '874KB' },
            { name: 'Competitor_Analysis.xlsx', size: '2.5MB' },
        ];
        const randomFile = dummyFiles[Math.floor(Math.random() * dummyFiles.length)];
        if (!uploadedFiles.some(f => f.name === randomFile.name)) {
            setUploadedFiles(prev => [...prev, randomFile]);
        }
    };
    
    const handleRemoveFile = (fileName: string) => {
        setUploadedFiles(prev => prev.filter(f => f.name !== fileName));
    };

    const handleStartMeeting = () => {
        if (meetingName.trim()) {
            const langName = languages.find(l => l.code === selectedLanguage)?.name || 'English (US)';
            setMeetingLanguage(langName);
            setMeetingState('in-meeting');
        }
    };

    const handleEndMeeting = () => {
        setMeetingState('pre-meeting');
        // Optionally reset other states
        setIsSuperModeOn(false);
        setShowTranslation(false);
        setUploadedFiles([]);
    }

    return (
        <div className="bg-gray-900 text-gray-300 h-full flex p-2">
            <div className="bg-gray-800 border border-gray-700 rounded-xl shadow-2xl flex flex-col h-full w-full overflow-hidden">
                {/* App Header (Persistent) */}
                <header className="flex items-center justify-between p-3 border-b border-gray-700 flex-shrink-0">
                    <div className="flex items-center space-x-3">
                         <div className="bg-blue-accent p-2 rounded-lg">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a3.12 3.12 0 0 1 3 3.99V12a3.12 3.12 0 0 1-3 3.99z"/><path d="M12 2a3.12 3.12 0 0 0-3 3.99V12a3.12 3.12 0 0 0 3 3.99z"/><line x1="12" x2="12" y1="19" y2="22"/><line x1="8" x2="16" y1="20" y2="20"/></svg>
                        </div>
                        <h1 className="text-md font-bold text-white">MeetingAI Desktop</h1>
                    </div>
                    <div className="flex items-center space-x-4">
                        {!isLoggedIn ? (
                             <>
                                <span className="text-sm text-gray-400">Not Logged In</span>
                                <button 
                                    onClick={() => setIsLoggedIn(true)} 
                                    className="bg-gray-700 hover:bg-gray-600 text-white text-sm px-4 py-2 rounded-lg font-semibold transition-colors"
                                >
                                    Log In
                                </button>
                            </>
                        ) : (
                            <>
                                <div className="flex items-center space-x-2">
                                    <img src={currentUser.avatarUrl} alt={currentUser.name} className="w-8 h-8 rounded-full" />
                                    <div className="text-sm">
                                        <div className="font-medium text-white">{currentUser.name}</div>
                                    </div>
                                </div>
                                <a href="#" className="text-sm font-semibold text-blue-accent hover:underline">View Analytics</a>
                            </>
                        )}
                    </div>
                </header>

                {/* Main Content Area (Conditional) */}
                <main className="flex-1 overflow-y-auto">
                    {meetingState === 'pre-meeting' ? (
                        <div className="flex flex-col items-center justify-center h-full p-4 sm:p-8">
                            <div className="w-full max-w-lg text-center">
                                <div className="mx-auto bg-blue-accent p-3 rounded-full w-fit mb-4">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a3.12 3.12 0 0 1 3 3.99V12a3.12 3.12 0 0 1-3 3.99z"/><path d="M12 2a3.12 3.12 0 0 0-3 3.99V12a3.12 3.12 0 0 0 3 3.99z"/><line x1="12" x2="12" y1="19" y2="22"/><line x1="8" x2="16" y1="20" y2="20"/></svg>
                                </div>
                                <h2 className="text-2xl font-bold text-white mb-2">Prepare Your Meeting</h2>
                                <p className="text-gray-400 mb-8">Set up your meeting name, context, and AI agent instructions.</p>

                                <div className="space-y-6 text-left">
                                    <div>
                                        <label htmlFor="meeting-name" className="block text-sm font-medium text-gray-300 mb-1">Meeting Name</label>
                                        <input
                                            id="meeting-name"
                                            type="text"
                                            value={meetingName}
                                            onChange={(e) => setMeetingName(e.target.value)}
                                            placeholder="e.g., Q4 Strategy Session"
                                            className="w-full bg-gray-700 text-white placeholder-gray-400 border border-gray-600 rounded-lg py-2 px-4 focus:outline-none focus:ring-2 focus:ring-blue-accent focus:border-transparent"
                                        />
                                    </div>

                                    <div>
                                        <label htmlFor="assistant-prompt" className="block text-sm font-medium text-gray-300 mb-1">AI Agent's Goal</label>
                                        <select
                                            id="assistant-prompt"
                                            value={selectedAssistantPrompt}
                                            onChange={(e) => setSelectedAssistantPrompt(e.target.value)}
                                            className="w-full bg-gray-700 text-white border border-gray-600 rounded-lg py-2.5 px-4 focus:outline-none focus:ring-2 focus:ring-blue-accent focus:border-transparent"
                                        >
                                            {assistantPrompts.map(prompt => (
                                                <option key={prompt.id} value={prompt.id}>{prompt.name}</option>
                                            ))}
                                        </select>
                                    </div>
                                    
                                    <div>
                                        <label htmlFor="meeting-language" className="block text-sm font-medium text-gray-300 mb-1">Meeting Language</label>
                                        <select
                                            id="meeting-language"
                                            value={selectedLanguage}
                                            onChange={(e) => setSelectedLanguage(e.target.value)}
                                            className="w-full bg-gray-700 text-white border border-gray-600 rounded-lg py-2.5 px-4 focus:outline-none focus:ring-2 focus:ring-blue-accent focus:border-transparent"
                                        >
                                            {languages.map(lang => (
                                                <option key={lang.code} value={lang.code}>{lang.name}</option>
                                            ))}
                                        </select>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-300 mb-1">Context Documents</label>
                                        <div 
                                            onClick={handleAddFile}
                                            className="border-2 border-dashed border-gray-600 rounded-lg p-6 text-center cursor-pointer hover:border-blue-accent hover:bg-gray-700/50 transition-colors">
                                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mx-auto h-8 w-8 text-gray-500 mb-2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/></svg>
                                            <p className="text-sm text-gray-400">Click to upload documents</p>
                                            <p className="text-xs text-gray-500">(PDF, DOCX, XLSX)</p>
                                        </div>
                                        {uploadedFiles.length > 0 && (
                                            <div className="mt-4 space-y-2">
                                                {uploadedFiles.map(file => (
                                                    <div key={file.name} className="bg-gray-700 p-2 rounded-md flex items-center justify-between">
                                                        <div className="flex items-center gap-2">
                                                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-400"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
                                                            <span className="text-sm text-white">{file.name}</span>
                                                            <span className="text-xs text-gray-500">{file.size}</span>
                                                        </div>
                                                        <button onClick={() => handleRemoveFile(file.name)} className="text-gray-500 hover:text-red-500">
                                                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
                                                        </button>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>

                                <button 
                                    onClick={handleStartMeeting}
                                    disabled={!meetingName.trim()}
                                    className="mt-8 w-full bg-blue-accent text-white font-semibold py-3 rounded-lg hover:bg-blue-600 transition-colors disabled:bg-gray-600 disabled:cursor-not-allowed">
                                    Start Meeting
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="flex flex-col h-full">
                            {/* In-meeting Header */}
                            <div className="flex items-center justify-between p-3 border-b border-gray-700 flex-shrink-0">
                                <div className="flex items-center space-x-3">
                                    <span className="relative flex h-3 w-3">
                                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                                        <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
                                    </span>
                                    <h2 className="font-semibold text-white">Live: {meetingName}</h2>
                                    <span className="text-xs bg-gray-700 text-gray-400 px-2 py-1 rounded-md">{meetingLanguage}</span>
                                </div>
                                <div className="flex items-center space-x-4">
                                    <Toggle isEnabled={isSuperModeOn} onToggle={() => setIsSuperModeOn(!isSuperModeOn)} label="Super Mode" />
                                    <button onClick={handleEndMeeting} className="text-xs bg-red-500/20 text-red-400 px-3 py-1.5 rounded-md hover:bg-red-500/40 transition-colors">End Meeting</button>
                                </div>
                            </div>
                             {/* In-meeting Main Content */}
                            <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 p-4 overflow-hidden">
                                 <div className="flex flex-col gap-4 overflow-y-auto">
                                    {/* Assistant Tabs */}
                                    <div className="bg-gray-900/50 p-4 rounded-lg flex-1 flex flex-col">
                                         <div className="flex border-b border-gray-700 mb-3">
                                            <button onClick={() => setActiveTab('cues')} className={`px-4 py-2 text-sm font-medium transition-colors ${activeTab === 'cues' ? 'border-b-2 border-blue-accent text-white' : 'text-gray-400 hover:text-white'}`}>AI Cues</button>
                                            <button onClick={() => setActiveTab('chat')} className={`px-4 py-2 text-sm font-medium transition-colors ${activeTab === 'chat' ? 'border-b-2 border-blue-accent text-white' : 'text-gray-400 hover:text-white'}`}>Ask AI</button>
                                        </div>

                                        {activeTab === 'cues' && (
                                            <div className="space-y-3 pr-2 overflow-y-auto">
                                                {aiCues.map((cue, index) => (
                                                    <div key={index} className="bg-gray-700/70 p-3 rounded-md flex items-start space-x-3 hover:bg-gray-700 transition-colors">
                                                        <span className="text-lg mt-0.5">{cue.icon}</span>
                                                        <p className="text-sm text-gray-300">{cue.text}</p>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                        {activeTab === 'chat' && (
                                           <div className="flex-1 flex flex-col overflow-hidden">
                                                <div className="flex-1 space-y-4 pr-2 overflow-y-auto">
                                                    {chatHistory.map((msg, i) => (
                                                        <div key={i} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                                                            <div className={`p-3 rounded-lg max-w-xs text-sm ${msg.sender === 'user' ? 'bg-blue-accent text-white' : 'bg-gray-700 text-gray-300'}`}>
                                                                {msg.text}
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                                <div className="mt-4 flex space-x-2">
                                                    <input 
                                                        type="text"
                                                        value={userInput}
                                                        onChange={(e) => setUserInput(e.target.value)}
                                                        onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                                                        placeholder="Ask a question..."
                                                        className="flex-1 w-full bg-gray-700 text-white rounded-md p-2 border border-gray-600 focus:ring-blue-accent focus:border-blue-accent"
                                                    />
                                                    <button onClick={handleSendMessage} className="bg-blue-accent p-2 rounded-md hover:bg-blue-600">
                                                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m22 2-7 20-4-9-9-4Z"/><path d="m22 2-11 11"/></svg>
                                                    </button>
                                                </div>
                                           </div>
                                        )}
                                    </div>
                                    {/* Notes */}
                                    <div className="bg-gray-900/50 p-4 rounded-lg flex-1 flex flex-col min-h-[200px]">
                                        <h3 className="text-lg font-semibold text-white mb-3">My Notes</h3>
                                        <textarea 
                                            className="w-full flex-1 bg-gray-700/50 text-gray-300 rounded-md p-2 border border-transparent focus:ring-2 focus:ring-blue-accent focus:border-transparent resize-none"
                                            placeholder="Start typing your notes here..."
                                        />
                                    </div>
                                </div>

                                {/* Right Column: Transcript */}
                                <div className="lg:col-span-2 bg-gray-900/50 p-4 rounded-lg flex flex-col h-full">
                                    <div className="flex justify-between items-center mb-3 flex-shrink-0">
                                        <h3 className="text-lg font-semibold text-white">Live Transcript</h3>
                                        <Toggle isEnabled={showTranslation} onToggle={() => setShowTranslation(!showTranslation)} label="Show Translation" />
                                    </div>
                                    <div className="flex-1 overflow-y-auto pr-2 space-y-4">
                                        {liveTranscript.map((item, index) => (
                                            <React.Fragment key={index}>
                                                <LiveTranscriptItem item={item} showTranslation={showTranslation} />
                                                {item.speaker === 'Them' && isSuperModeOn && (
                                                    <div className="my-4 ml-12">
                                                        <h4 className="text-sm font-bold text-purple-accent mb-2 flex items-center gap-2">
                                                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M15 4.13a8 8 0 0 1 0 15.74"/><path d="M9 20.13a8 8 0 0 1 0-15.74"/><path d="M12 2v20"/><path d="M22 12H2"/></svg>
                                                            Super Mode Suggestions
                                                        </h4>
                                                        <div className="flex flex-wrap gap-2">
                                                            {suggestedReplies.map((reply, i) => (
                                                                <button key={i} className="px-3 py-1.5 text-xs bg-gray-700 hover:bg-purple-accent hover:text-white rounded-full transition-colors">
                                                                    {reply}
                                                                </button>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}
                                            </React.Fragment>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </main>
            </div>
        </div>
    );
};

export default DesktopAppView;