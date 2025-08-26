import React, { useState } from 'react';
import { users } from '../constants';
import { Skill } from '../types';

interface SkillEditModalProps {
    skills: Skill[];
    onSkillsChange: (skills: Skill[]) => void;
    onSave: () => void;
    onClose: () => void;
}

const SkillEditModal: React.FC<SkillEditModalProps> = ({ skills, onSkillsChange, onSave, onClose }) => {

    const handleSkillChange = (index: number, field: 'name' | 'description', value: string) => {
        const newSkills = [...skills];
        newSkills[index] = { ...newSkills[index], [field]: value };
        onSkillsChange(newSkills);
    };

    const handleAddSkill = () => {
        const newSkill: Skill = {
            id: `new-${Date.now()}`,
            name: 'New Skill',
            description: 'AI analysis: Define what this skill represents and how it contributes to your role\'s success.',
            score: 0,
        };
        onSkillsChange([...skills, newSkill]);
    };

    const handleDeleteSkill = (id: string) => {
        onSkillsChange(skills.filter(skill => skill.id !== id));
    };

    return (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 animate-fade-in-fast" onClick={onClose}>
            <div className="bg-gray-800 rounded-xl border border-gray-700 w-full max-w-2xl max-h-[90vh] flex flex-col" onClick={e => e.stopPropagation()}>
                <div className="flex items-center justify-between p-4 border-b border-gray-700 flex-shrink-0">
                    <h3 className="text-lg font-bold text-white">Edit Your Skill Set</h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
                    </button>
                </div>

                <div className="p-6 overflow-y-auto space-y-4">
                    {skills.map((skill, index) => (
                        <div key={skill.id} className="bg-gray-900/50 p-4 rounded-lg border border-gray-700">
                            <div className="flex justify-between items-center mb-2">
                                <input
                                    type="text"
                                    value={skill.name}
                                    onChange={(e) => handleSkillChange(index, 'name', e.target.value)}
                                    className="bg-transparent text-white font-semibold text-md w-full focus:outline-none"
                                />
                                <button onClick={() => handleDeleteSkill(skill.id)} className="text-gray-500 hover:text-red-500 transition-colors">
                                     <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                                </button>
                            </div>
                            <textarea
                                value={skill.description}
                                onChange={(e) => handleSkillChange(index, 'description', e.target.value)}
                                rows={3}
                                className="w-full bg-gray-700/50 text-gray-300 text-sm rounded-md p-2 border border-gray-600 focus:ring-2 focus:ring-blue-accent focus:border-transparent resize-y"
                            />
                        </div>
                    ))}
                </div>

                <div className="p-4 border-t border-gray-700 flex justify-between items-center flex-shrink-0">
                    <button onClick={handleAddSkill} className="bg-gray-700 hover:bg-gray-600 text-white text-sm px-3 py-1.5 rounded-md font-semibold transition-colors">+ Add New Skill</button>
                    <div className="space-x-2">
                        <button onClick={onClose} className="text-gray-300 hover:text-white text-sm px-4 py-2 rounded-lg font-semibold transition-colors">Cancel</button>
                        <button onClick={onSave} className="bg-blue-accent text-white px-4 py-2 rounded-lg font-semibold hover:bg-blue-600 transition-colors">Save Changes</button>
                    </div>
                </div>
            </div>
        </div>
    );
};


const SettingsView: React.FC = () => {
    const currentUser = users['user1'];
    const [jobDescription, setJobDescription] = useState(currentUser.jobDescription || '');
    const [isGenerating, setIsGenerating] = useState(false);
    const [generatedSkills, setGeneratedSkills] = useState<Skill[] | null>(null);

    const [isSkillModalOpen, setIsSkillModalOpen] = useState(false);
    const [skillsToEdit, setSkillsToEdit] = useState<Skill[]>([]);

    const handleGenerateSkills = () => {
        setIsGenerating(true);
        setGeneratedSkills(null);
        setTimeout(() => {
            const skillsWithDefaults = (currentUser.skills || []).map(s => ({
                ...s,
                description: s.description || 'AI analysis: [Add description]'
            }));
            setGeneratedSkills(skillsWithDefaults);
            setIsGenerating(false);
        }, 2000);
    };

    const handleOpenSkillModal = () => {
        if(generatedSkills){
            setSkillsToEdit([...generatedSkills]);
            setIsSkillModalOpen(true);
        }
    };
    
    const handleSaveSkills = () => {
        setGeneratedSkills(skillsToEdit);
        setIsSkillModalOpen(false);
    };


    return (
        <div className="space-y-8 max-w-4xl mx-auto">
            <h2 className="text-3xl font-bold text-white">Settings</h2>

            {isSkillModalOpen && (
                <SkillEditModal 
                    skills={skillsToEdit}
                    onSkillsChange={setSkillsToEdit}
                    onSave={handleSaveSkills}
                    onClose={() => setIsSkillModalOpen(false)}
                />
            )}

            {/* Profile Settings */}
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <h3 className="text-lg font-semibold text-white mb-4">Profile</h3>
                <div className="flex items-center space-x-4">
                    <img src={currentUser.avatarUrl} alt={currentUser.name} className="w-16 h-16 rounded-full" />
                    <div>
                        <button className="bg-gray-700 hover:bg-gray-600 text-white text-sm px-3 py-1.5 rounded-md">Change Photo</button>
                        <p className="text-xs text-gray-400 mt-2">JPG, GIF or PNG. 1MB max.</p>
                    </div>
                </div>
                <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className="text-sm font-medium text-gray-400">Full Name</label>
                        <input type="text" defaultValue={currentUser.name} className="mt-1 w-full bg-gray-700 text-white rounded-md p-2 border border-gray-600 focus:ring-blue-accent focus:border-blue-accent" />
                    </div>
                    <div>
                        <label className="text-sm font-medium text-gray-400">Email</label>
                        <input type="email" defaultValue="alex.j@example.com" className="mt-1 w-full bg-gray-700 text-white rounded-md p-2 border border-gray-600 focus:ring-blue-accent focus:border-blue-accent" />
                    </div>
                </div>
                <div className="mt-6 flex justify-end">
                    <button className="bg-blue-accent text-white px-4 py-2 rounded-lg font-semibold hover:bg-blue-600 transition-colors">Save Changes</button>
                </div>
            </div>

            {/* My Role & Skills */}
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <h3 className="text-lg font-semibold text-white mb-4">My Role & Skills</h3>
                <p className="text-sm text-gray-400 mb-4">Describe your role, and our AI will identify key skills to track in your meetings. This helps personalize your analytics and coaching.</p>
                
                <div>
                    <label htmlFor="job-description" className="text-sm font-medium text-gray-300">Your Role Description</label>
                    <textarea
                        id="job-description"
                        rows={5}
                        value={jobDescription}
                        onChange={(e) => setJobDescription(e.target.value)}
                        placeholder="e.g., I am a sales representative responsible for..."
                        className="mt-1 w-full bg-gray-700 text-white placeholder-gray-500 border border-gray-600 rounded-lg py-2 px-4 focus:outline-none focus:ring-2 focus:ring-blue-accent resize-none"
                    />
                </div>

                <div className="mt-4 flex items-center justify-between">
                    <p className="text-xs text-gray-500">The more detailed you are, the better the AI can tailor your skill set.</p>
                    <button 
                        onClick={handleGenerateSkills}
                        disabled={isGenerating}
                        className="bg-purple-accent text-white px-4 py-2 rounded-lg font-semibold hover:bg-purple-600 transition-colors disabled:bg-gray-600 disabled:cursor-not-allowed flex items-center"
                    >
                        {isGenerating ? (
                            <>
                                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                Analyzing...
                            </>
                        ) : 'Generate My Skill Set'}
                    </button>
                </div>

                {generatedSkills && (
                    <div className="mt-6 pt-4 border-t border-gray-700">
                        <div className="flex justify-between items-center mb-3">
                           <div>
                                <h4 className="text-md font-semibold text-white">Your Identified Skills:</h4>
                                <p className="text-sm text-gray-400">We'll track these skills in your meetings to provide personalized coaching.</p>
                           </div>
                           <button onClick={handleOpenSkillModal} className="text-sm font-semibold text-blue-accent hover:underline">
                                Edit Skills
                           </button>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {generatedSkills.map(skill => (
                                <span key={skill.id} className="bg-gray-700 text-gray-300 text-sm font-medium px-3 py-1.5 rounded-full">{skill.name}</span>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Billing Information */}
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <h3 className="text-lg font-semibold text-white mb-4">Billing</h3>
                <div className="bg-gray-700 p-4 rounded-lg flex justify-between items-center">
                    <div>
                        <p className="font-semibold text-white">Pro Plan</p>
                        <p className="text-sm text-gray-400">Next payment of $49 on August 1, 2024</p>
                    </div>
                    <button className="text-blue-accent hover:underline text-sm font-semibold">Manage Plan</button>
                </div>
            </div>

            {/* Integrations */}
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <h3 className="text-lg font-semibold text-white mb-4">Integrations</h3>
                <div className="space-y-4">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center">
                            <div className="text-xl mr-3">📅</div>
                            <div>
                                <p className="font-medium text-white">Google Calendar</p>
                                <p className="text-sm text-gray-400">Sync your meetings automatically</p>
                            </div>
                        </div>
                        <button className="bg-green-600 text-white px-3 py-1.5 rounded-lg text-sm font-semibold">Connected</button>
                    </div>
                    <div className="flex justify-between items-center">
                        <div className="flex items-center">
                            <div className="text-xl mr-3">💼</div>
                            <div>
                                <p className="font-medium text-white">Salesforce</p>
                                <p className="text-sm text-gray-400">Sync meeting notes to contacts</p>
                            </div>
                        </div>
                        <button className="bg-gray-700 hover:bg-gray-600 text-white text-sm px-3 py-1.5 rounded-md">Connect</button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SettingsView;