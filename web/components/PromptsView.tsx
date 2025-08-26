import React from 'react';
import { aiPrompts } from '../constants';

const PromptsView: React.FC = () => {
    return (
        <div className="space-y-8 max-w-5xl mx-auto">
            <div className="flex justify-between items-center">
                <h2 className="text-3xl font-bold text-white">AI Prompts</h2>
                <button className="bg-blue-accent text-white px-4 py-2 rounded-lg font-semibold hover:bg-blue-600 transition-colors">
                    + Create New Prompt
                </button>
            </div>

            {/* Create New Prompt Form (Dummy) */}
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <h3 className="text-lg font-semibold text-white mb-4">Create a Custom Prompt</h3>
                <div className="space-y-4">
                    <div>
                        <label htmlFor="prompt-name" className="text-sm font-medium text-gray-300">Prompt Name</label>
                        <input
                            id="prompt-name"
                            type="text"
                            placeholder="e.g., Sales Follow-up Checklist"
                            className="mt-1 w-full bg-gray-700 text-white placeholder-gray-500 border border-gray-600 rounded-lg py-2 px-4 focus:outline-none focus:ring-2 focus:ring-blue-accent"
                        />
                    </div>
                     <div>
                        <label htmlFor="prompt-text" className="text-sm font-medium text-gray-300">Prompt Instructions</label>
                        <textarea
                            id="prompt-text"
                            rows={4}
                            placeholder="Analyze this sales call. Identify customer pain points, buying signals, and any objections..."
                            className="mt-1 w-full bg-gray-700 text-white placeholder-gray-500 border border-gray-600 rounded-lg py-2 px-4 focus:outline-none focus:ring-2 focus:ring-blue-accent resize-none"
                        />
                    </div>
                    <div>
                        <label className="text-sm font-medium text-gray-300">Prompt Usage</label>
                        <p className="text-xs text-gray-400">Select where this prompt can be used.</p>
                        <div className="mt-2 flex gap-6">
                            <label className="flex items-center space-x-2 cursor-pointer">
                                <input type="checkbox" className="h-4 w-4 rounded bg-gray-700 border-gray-600 text-blue-accent focus:ring-blue-accent" />
                                <span className="text-sm text-gray-200">Meeting Summary</span>
                            </label>
                             <label className="flex items-center space-x-2 cursor-pointer">
                                <input type="checkbox" className="h-4 w-4 rounded bg-gray-700 border-gray-600 text-blue-accent focus:ring-blue-accent" />
                                <span className="text-sm text-gray-200">Meeting Assistant</span>
                            </label>
                        </div>
                    </div>
                </div>
                <div className="mt-6 flex justify-end">
                    <button className="bg-blue-accent text-white px-4 py-2 rounded-lg font-semibold hover:bg-blue-600 transition-colors">Save Prompt</button>
                </div>
            </div>

            {/* Prompt List */}
            <div className="space-y-4">
                <div>
                    <h3 className="text-xl font-bold text-white">Your Prompts</h3>
                    <p className="text-sm text-gray-400">These prompts will be available to generate summaries for your meetings or assist you live.</p>
                </div>
                <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
                    <ul className="divide-y divide-gray-700">
                        {aiPrompts.map(prompt => (
                            <li key={prompt.id} className="p-4">
                                <div className="flex justify-between items-start">
                                    <div>
                                        <div className="flex items-center gap-3 flex-wrap">
                                            <p className="font-semibold text-white">{prompt.name}</p>
                                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${prompt.type === 'default' ? 'bg-gray-600 text-gray-300' : 'bg-purple-accent/30 text-purple-300'}`}>
                                                {prompt.type}
                                            </span>
                                            {prompt.tags?.map(tag => (
                                                <span key={tag} className="text-xs font-medium px-2 py-0.5 rounded-full bg-blue-accent/30 text-blue-300">
                                                    {tag}
                                                </span>
                                            ))}
                                        </div>
                                        <p className="text-sm text-gray-400 mt-2 max-w-2xl">{prompt.text}</p>
                                    </div>
                                    <div className="flex-shrink-0 ml-4 mt-1">
                                        <button className="text-sm text-blue-accent hover:underline">Edit</button>
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

export default PromptsView;