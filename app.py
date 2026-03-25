<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fi/le Logo Tasarımı</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        * {
            font-family: 'Space Grotesk', sans-serif;
        }
        
        .mono {
            font-family: 'JetBrains Mono', monospace;
        }
        
        /* Grid Background */
        .blueprint-grid {
            background-image: 
                linear-gradient(rgba(59, 130, 246, 0.1) 1px, transparent 1px),
                linear-gradient(90deg, rgba(59, 130, 246, 0.1) 1px, transparent 1px);
            background-size: 40px 40px;
            animation: gridMove 20s linear infinite;
        }
        
        @keyframes gridMove {
            0% { background-position: 0 0; }
            100% { background-position: 40px 40px; }
        }
        
        /* Glitch Effect */
        .glitch {
            position: relative;
        }
        
        .glitch::before,
        .glitch::after {
            content: attr(data-text);
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
        }
        
        .glitch::before {
            left: 2px;
            text-shadow: -2px 0 #ff00ff;
            clip: rect(24px, 550px, 90px, 0);
            animation: glitch-anim-2 3s infinite linear alternate-reverse;
        }
        
        .glitch::after {
            left: -2px;
            text-shadow: -2px 0 #00ffff;
            clip: rect(85px, 550px, 140px, 0);
            animation: glitch-anim 2.5s infinite linear alternate-reverse;
        }
        
        @keyframes glitch-anim {
            0% { clip: rect(10px, 9999px, 85px, 0); }
            20% { clip: rect(63px, 9999px, 130px, 0); }
            40% { clip: rect(25px, 9999px, 145px, 0); }
            60% { clip: rect(89px, 9999px, 55px, 0); }
            80% { clip: rect(45px, 9999px, 99px, 0); }
            100% { clip: rect(12px, 9999px, 120px, 0); }
        }
        
        @keyframes glitch-anim-2 {
            0% { clip: rect(65px, 9999px, 100px, 0); }
            20% { clip: rect(20px, 9999px, 75px, 0); }
            40% { clip: rect(90px, 9999px, 140px, 0); }
            60% { clip: rect(15px, 9999px, 60px, 0); }
            80% { clip: rect(120px, 9999px, 160px, 0); }
            100% { clip: rect(5px, 9999px, 80px, 0); }
        }
        
        /* Blueprint Lines */
        .blueprint-line {
            stroke-dasharray: 1000;
            stroke-dashoffset: 1000;
            animation: drawLine 3s ease-out forwards;
        }
        
        @keyframes drawLine {
            to { stroke-dashoffset: 0; }
        }
        
        /* Hover Effects */
        .logo-card {
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .logo-card:hover {
            transform: translateY(-8px) scale(1.02);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
        }
        
        /* Cursor Blink */
        .cursor-blink {
            animation: blink 1s step-end infinite;
        }
        
        @keyframes blink {
            50% { opacity: 0; }
        }
        
        /* Morphing Shape */
        .morph-shape {
            animation: morph 8s ease-in-out infinite;
        }
        
        @keyframes morph {
            0%, 100% { border-radius: 0%; }
            33% { border-radius: 30% 70% 70% 30% / 30% 30% 70% 70%; }
            66% { border-radius: 70% 30% 30% 70% / 70% 70% 30% 30%; }
        }
        
        /* Scanline */
        .scanline {
            background: linear-gradient(
                to bottom,
                transparent 50%,
                rgba(59, 130, 246, 0.1) 50%
            );
            background-size: 100% 4px;
            animation: scanline 10s linear infinite;
        }
        
        @keyframes scanline {
            0% { transform: translateY(0); }
            100% { transform: translateY(10px); }
        }
        
        /* Neon Glow */
        .neon-glow {
            box-shadow: 
                0 0 5px rgba(59, 130, 246, 0.5),
                0 0 20px rgba(59, 130, 246, 0.3),
                0 0 40px rgba(59, 130, 246, 0.1);
        }
        
        /* Tab Active State */
        .tab-active {
            background: rgba(59, 130, 246, 0.1);
            border-bottom: 2px solid #3b82f6;
        }
    </style>
</head>
<body class="bg-slate-950 text-white min-h-screen blueprint-grid overflow-x-hidden">

    <!-- Header -->
    <header class="fixed top-0 w-full bg-slate-950/80 backdrop-blur-md border-b border-slate-800 z-50">
        <div class="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center mono font-bold text-xl">
                    F<span class="text-xs">/</span>l
                </div>
                <span class="font-semibold tracking-wide">Fi/le Design System</span>
            </div>
            <div class="flex gap-6 text-sm text-slate-400">
                <span class="mono">v1.0.0</span>
                <span class="text-blue-400">● Live Preview</span>
            </div>
        </div>
    </header>

    <!-- Main Content -->
    <main class="pt-24 pb-20 px-6 max-w-7xl mx-auto">
        
        <!-- Hero Section -->
        <section class="text-center mb-20 relative">
            <div class="absolute inset-0 bg-blue-500/20 blur-3xl rounded-full transform -translate-y-1/2"></div>
            
            <div class="relative z-10">
                <div class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-slate-900/50 border border-slate-700 mb-6">
                    <span class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                    <span class="text-sm text-slate-300 mono">Architecture × Software</span>
                </div>
                
                <h1 class="text-7xl md:text-9xl font-bold mb-6 tracking-tighter">
                    <span class="glitch inline-block" data-text="Fi/le">Fi/le</span>
                </h1>
                
                <p class="text-xl md:text-2xl text-slate-400 max-w-2xl mx-auto leading-relaxed">
                    Mimari hassasiyet ve yazılım keskinliğinin kesişim noktasında bir kimlik
                </p>
                
                <div class="mt-8 flex justify-center gap-4 text-sm mono text-slate-500">
                    <span>Blueprint Mode: ON</span>
                    <span>//</span>
                    <span>Compile: Success</span>
                </div>
            </div>
        </section>

        <!-- Concept Explanation -->
        <section class="mb-16 grid md:grid-cols-3 gap-6">
            <div class="bg-slate-900/50 border border-slate-800 p-6 rounded-xl hover:border-blue-500/50 transition-colors">
                <div class="w-12 h-12 bg-blue-500/10 rounded-lg flex items-center justify-center mb-4">
                    <svg class="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
                    </svg>
                </div>
                <h3 class="text-lg font-semibold mb-2">Dosya Yapısı</h3>
                <p class="text-slate-400 text-sm">".file" uzantısı yazılım kökenini, "Fi" ise mimari formu temsil eder. Slash (/) her iki dünyayı birleştirir.</p>
            </div>
            
            <div class="bg-slate-900/50 border border-slate-800 p-6 rounded-xl hover:border-purple-500/50 transition-colors">
                <div class="w-12 h-12 bg-purple-500/10 rounded-lg flex items-center justify-center mb-4">
                    <svg class="w-6 h-6 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"></path>
                    </svg>
                </div>
                <h3 class="text-lg font-semibold mb-2">Modüler Grid</h3>
                <p class="text-slate-400 text-sm">Mimari planların grid sistemi ile yazılım layout'larının pixel-perfect hizalaması arasındaki benzerlik.</p>
            </div>
            
            <div class="bg-slate-900/50 border border-slate-800 p-6 rounded-xl hover:border-cyan-500/50 transition-colors">
                <div class="w-12 h-12 bg-cyan-500/10 rounded-lg flex items-center justify-center mb-4">
                    <svg class="w-6 h-6 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path>
                    </svg>
                </div>
                <h3 class="text-lg font-semibold mb-2">Syntax & Structure</h3>
                <p class="text-slate-400 text-sm">Kodun syntax'ı kadar katı, mimarinin estetiği kadar akıcı bir dil yaratma felsefesi.</p>
            </div>
        </section>

        <!-- Logo Variations -->
        <section class="mb-20">
            <div class="flex items-center justify-between mb-8">
                <h2 class="text-3xl font-bold">Logo Varyasyonları</h2>
                <div class="flex gap-2 bg-slate-900 p-1 rounded-lg border border-slate-800">
                    <button onclick="switchTab('primary')" id="tab-primary" class="px-4 py-2 rounded-md text-sm font-medium transition-all tab-active">Ana Logo</button>
                    <button onclick="switchTab('icon')" id="tab-icon" class="px-4 py-2 rounded-md text-sm font-medium transition-all text-slate-400 hover:text-white">İkon</button>
                    <button onclick="switchTab('mono')" id="tab-mono" class="px-4 py-2 rounded-md text-sm font-medium transition-all text-slate-400 hover:text-white">Monokrom</button>
                </div>
            </div>

            <!-- Primary Logo Display -->
            <div id="content-primary" class="grid md:grid-cols-2 gap-8">
                <!-- Version 1: The Blueprint -->
                <div class="logo-card bg-slate-900 border border-slate-800 rounded-2xl p-12 relative overflow-hidden group">
                    <div class="absolute inset-0 blueprint-grid opacity-30"></div>
                    <div class="scanline absolute inset-0 pointer-events-none"></div>
                    
                    <div class="relative z-10 flex flex-col items-center">
                        <svg viewBox="0 0 200 100" class="w-full max-w-md mb-6">
                            <!-- Blueprint Lines -->
                            <line x1="20" y1="20" x2="180" y2="20" stroke="#3b82f6" stroke-width="0.5" class="blueprint-line" opacity="0.5"/>
                            <line x1="20" y1="80" x2="180" y2="80" stroke="#3b82f6" stroke-width="0.5" class="blueprint-line" opacity="0.5"/>
                            
                            <!-- Main Text -->
                            <text x="50" y="65" font-family="Space Grotesk" font-size="48" font-weight="700" fill="white">Fi</text>
                            
                            <!-- The Slash - Animated -->
                            <line x1="95" y1="25" x2="85" y2="75" stroke="#3b82f6" stroke-width="4" stroke-linecap="round">
                                <animate attributeName="stroke-dasharray" from="0,100" to="100,0" dur="2s" fill="freeze"/>
                            </line>
                            
                            <text x="105" y="65" font-family="JetBrains Mono" font-size="48" font-weight="400" fill="#94a3b8">le</text>
                            
                            <!-- Corner Markers -->
                            <circle cx="30" cy="30" r="2" fill="#3b82f6" opacity="0.5"/>
                            <circle cx="170" cy="30" r="2" fill="#3b82f6" opacity="0.5"/>
                            <circle cx="30" cy="70" r="2" fill="#3b82f6" opacity="0.5"/>
                            <circle cx="170" cy="70" r="2" fill="#3b82f6" opacity="0.5"/>
                        </svg>
                        
                        <div class="text-center">
                            <h3 class="text-xl font-semibold mb-2">Blueprint Edition</h3>
                            <p class="text-slate-400 text-sm">Mimari plan çizgileri ve yazılım grid'i</p>
                        </div>
                    </div>
                    
                    <div class="absolute top-4 right-4 w-3 h-3 bg-blue-500 rounded-full animate-pulse"></div>
                </div>

                <!-- Version 2: The Code -->
                <div class="logo-card bg-slate-900 border border-slate-800 rounded-2xl p-12 relative overflow-hidden group">
                    <div class="absolute inset-0 bg-gradient-to-br from-purple-900/20 to-slate-900"></div>
                    
                    <div class="relative z-10 flex flex-col items-center">
                        <div class="text-6xl md:text-7xl font-bold mono mb-6 tracking-tighter flex items-baseline">
                            <span class="text-white">Fi</span>
                            <span class="text-purple-400 mx-1">/</span>
                            <span class="text-slate-400">le</span>
                            <span class="cursor-blink text-purple-400 ml-1">_</span>
                        </div>
                        
                        <div class="w-full max-w-xs bg-slate-950 rounded-lg p-4 border border-slate-800 mono text-xs text-slate-500 mb-4">
                            <div class="flex gap-2 mb-2">
                                <div class="w-3 h-3 rounded-full bg-red-500/20"></div>
                                <div class="w-3 h-3 rounded-full bg-yellow-500/20"></div>
                                <div class="w-3 h-3 rounded-full bg-green-500/20"></div>
                            </div>
                            <p><span class="text-purple-400">const</span> <span class="text-blue-400">project</span> = <span class="text-green-400">"Fi/le"</span>;</p>
                            <p><span class="text-purple-400">import</span> { Architecture } <span class="text-purple-400">from</span> <span class="text-green-400">'./blueprint'</span>;</p>
                        </div>
                        
                        <div class="text-center">
                            <h3 class="text-xl font-semibold mb-2">Terminal Edition</h3>
                            <p class="text-slate-400 text-sm">Geliştirici ortamı estetiği</p>
                        </div>
                    </div>
                </div>

                <!-- Version 3: The Structure -->
                <div class="logo-card bg-slate-900 border border-slate-800 rounded-2xl p-12 relative overflow-hidden group md:col-span-2">
                    <div class="absolute inset-0 bg-gradient-to-r from-blue-600/10 via-transparent to-cyan-600/10"></div>
                    
                    <div class="relative z-10 flex flex-col md:flex-row items-center justify-between gap-12">
                        <div class="flex-1">
                            <svg viewBox="0 0 300 120" class="w-full max-w-lg">
                                <!-- 3D Isometric Effect -->
                                <g transform="translate(150, 60)">
                                    <!-- Shadow -->
                                    <path d="M -60 40 L 0 60 L 60 40 L 0 20 Z" fill="rgba(0,0,0,0.3)"/>
                                    
                                    <!-- F Block -->
                                    <path d="M -80 -20 L -40 -20 L -40 20 L -80 20 Z" fill="#1e293b" stroke="#3b82f6" stroke-width="2"/>
                                    <path d="M -80 -20 L -60 -40 L -20 -40 L -40 -20" fill="#334155" stroke="#3b82f6" stroke-width="2"/>
                                    <path d="M -40 -20 L -20 -40 L -20 0 L -40 20" fill="#0f172a" stroke="#3b82f6" stroke-width="2"/>
                                    <text x="-60" y="5" font-family="Space Grotesk" font-size="24" font-weight="700" fill="white" text-anchor="middle">F</text>
                                    
                                    <!-- i Block -->
                                    <path d="M -20 0 L 0 0 L 0 40 L -20 40 Z" fill="#1e293b" stroke="#3b82f6" stroke-width="2"/>
                                    <path d="M -20 0 L -10 -20 L 10 -20 L 0 0" fill="#334155" stroke="#3b82f6" stroke-width="2"/>
                                    <path d="M 0 0 L 10 -20 L 10 20 L 0 40" fill="#0f172a" stroke="#3b82f6" stroke-width="2"/>
                                    <circle cx="-10" cy="-25" r="3" fill="#3b82f6"/>
                                    
                                    <!-- Slash -->
                                    <path d="M 10 30 L 30 -30" stroke="#06b6d4" stroke-width="4" stroke-linecap="round"/>
                                    
                                    <!-- l Block -->
                                    <path d="M 30 -10 L 50 -10 L 50 30 L 30 30 Z" fill="#1e293b" stroke="#94a3b8" stroke-width="2"/>
                                    <path d="M 30 -10 L 40 -30 L 60 -30 L 50 -10" fill="#334155" stroke="#94a3b8" stroke-width="2"/>
                                    <path d="M 50 -10 L 60 -30 L 60 10 L 50 30" fill="#0f172a" stroke="#94a3b8" stroke-width="2"/>
                                    
                                    <!-- e Block -->
                                    <path d="M 60 0 L 100 0 L 100 40 L 60 40 Z" fill="#1e293b" stroke="#94a3b8" stroke-width="2"/>
                                    <path d="M 60 0 L 80 -20 L 120 -20 L 100 0" fill="#334155" stroke="#94a3b8" stroke-width="2"/>
                                    <path d="M 100 0 L 120 -20 L 120 20 L 100 40" fill="#0f172a" stroke="#94a3b8" stroke-width="2"/>
                                </g>
                            </svg>
                        </div>
                        
                        <div class="flex-1 text-left">
                            <h3 class="text-2xl font-semibold mb-3">Isometric Structure</h3>
                            <p class="text-slate-400 mb-4">3D mimari bloklar ve yazılım katmanları metaforu. Her harf bir modül, slash ise bağlantı katmanı.</p>
                            <div class="flex gap-3">
                                <span class="px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 text-xs border border-blue-500/20">3D Render</span>
                                <span class="px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-400 text-xs border border-cyan-500/20">Isometric</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Icon Tab Content -->
            <div id="content-icon" class="hidden grid md:grid-cols-3 gap-8">
                <div class="logo-card bg-slate-900 border border-slate-800 rounded-2xl p-12 flex flex-col items-center justify-center aspect-square">
                    <div class="w-24 h-24 bg-blue-600 rounded-2xl flex items-center justify-center text-4xl font-bold mono neon-glow mb-4">
                        F<span class="text-lg">/</span>l
                    </div>
                    <p class="text-sm text-slate-400">App Icon</p>
                </div>
                
                <div class="logo-card bg-slate-900 border border-slate-800 rounded-2xl p-12 flex flex-col items-center justify-center aspect-square">
                    <div class="w-24 h-24 border-2 border-blue-500 rounded-full flex items-center justify-center text-3xl font-bold mb-4 relative">
                        <span class="z-10">F/l</span>
                        <div class="absolute inset-0 border-2 border-cyan-400 rounded-full transform rotate-45 scale-75"></div>
                    </div>
                    <p class="text-sm text-slate-400">Favicon</p>
                </div>
                
                <div class="logo-card bg-slate-900 border border-slate-800 rounded-2xl p-12 flex flex-col items-center justify-center aspect-square">
                    <svg viewBox="0 0 100 100" class="w-24 h-24 mb-4">
                        <rect x="20" y="20" width="60" height="60" fill="none" stroke="#3b82f6" stroke-width="4" rx="10"/>
                        <line x1="35" y1="35" x2="65" y2="65" stroke="#06b6d4" stroke-width="4" stroke-linecap="round"/>
                        <circle cx="35" cy="35" r="4" fill="white"/>
                        <circle cx="65" cy="65" r="4" fill="white"/>
                    </svg>
                    <p class="text-sm text-slate-400">Abstract Mark</p>
                </div>
            </div>

            <!-- Monochrome Tab Content -->
            <div id="content-mono" class="hidden grid md:grid-cols-2 gap-8">
                <div class="logo-card bg-white rounded-2xl p-12 flex flex-col items-center justify-center">
                    <div class="text-6xl font-bold text-black mb-4 tracking-tighter">
                        Fi<span class="text-gray-400">/</span>le
                    </div>
                    <p class="text-sm text-gray-500">Light Background</p>
                </div>
                
                <div class="logo-card bg-black border border-gray-800 rounded-2xl p-12 flex flex-col items-center justify-center">
                    <div class="text-6xl font-bold text-white mb-4 tracking-tighter">
                        Fi<span class="text-gray-500">/</span>le
                    </div>
                    <p class="text-sm text-gray-500">Dark Background</p>
                </div>
            </div>
        </section>

        <!-- Color Palette -->
        <section class="mb-20">
            <h2 class="text-3xl font-bold mb-8">Renk Paleti</h2>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div class="group cursor-pointer">
                    <div class="h-32 bg-blue-600 rounded-xl mb-3 relative overflow-hidden">
                        <div class="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                    </div>
                    <p class="font-mono text-sm font-bold">Blueprint Blue</p>
                    <p class="text-xs text-slate-500 mono">#2563EB</p>
                </div>
                <div class="group cursor-pointer">
                    <div class="h-32 bg-cyan-500 rounded-xl mb-3 relative overflow-hidden">
                        <div class="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                    </div>
                    <p class="font-mono text-sm font-bold">Code Cyan</p>
                    <p class="text-xs text-slate-500 mono">#06B6D4</p>
                </div>
                <div class="group cursor-pointer">
                    <div class="h-32 bg-slate-900 border border-slate-700 rounded-xl mb-3 relative overflow-hidden">
                        <div class="absolute inset-0 bg-white/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                    </div>
                    <p class="font-mono text-sm font-bold">Dark Mode</p>
                    <p class="text-xs text-slate-500 mono">#0F172A</p>
                </div>
                <div class="group cursor-pointer">
                    <div class="h-32 bg-purple-600 rounded-xl mb-3 relative overflow-hidden">
                        <div class="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                    </div>
                    <p class="font-mono text-sm font-bold">Compile Purple</p>
                    <p class="text-xs text-slate-500 mono">#9333EA</p>
                </div>
            </div>
        </section>

        <!-- Typography -->
        <section class="mb-20">
            <h2 class="text-3xl font-bold mb-8">Tipografi</h2>
            <div class="bg-slate-900 border border-slate-800 rounded-2xl p-8 md:p-12">
                <div class="grid md:grid-cols-2 gap-12">
                    <div>
                        <h3 class="text-sm text-slate-500 mb-4 mono">PRIMARY FONT</h3>
                        <p class="text-5xl font-bold mb-4" style="font-family: 'Space Grotesk'">Space Grotesk</p>
                        <p class="text-slate-400 mb-6">Modern, geometrik ve teknik. Mimari çizimlerin hassasiyetini yansıtır.</p>
                        <div class="space-y-2 text-sm text-slate-500 mono">
                            <p>Aa Bb Cc Dd Ee Ff Gg</p>
                            <p>1234567890</p>
                            <p>!@#$%^&*()</p>
                        </div>
                    </div>
                    <div>
                        <h3 class="text-sm text-slate-500 mb-4 mono">MONO FONT</h3>
                        <p class="text-5xl font-bold mb-4 mono">JetBrains Mono</p>
                        <p class="text-slate-400 mb-6">Kod editörleri için optimize, yazılım geliştirme kültürünü temsil eder.</p>
                        <div class="space-y-2 text-sm text-slate-500 mono">
                            <p>function build() { }</p>
                            <p>const file = new Fi/le();</p>
                            <p>&lt;Architecture /&gt;</p>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Mockups -->
        <section class="mb-20">
            <h2 class="text-3xl font-bold mb-8">Uygulama Örnekleri</h2>
            <div class="grid md:grid-cols-3 gap-6">
                <!-- Business Card -->
                <div class="logo-card bg-slate-900 border border-slate-800 rounded-xl p-6 aspect-[3/2] flex flex-col justify-between relative overflow-hidden group">
                    <div class="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full transform translate-x-16 -translate-y-16"></div>
                    <div class="relative z-10">
                        <div class="text-2xl font-bold tracking-tighter mb-1">Fi/le</div>
                        <div class="text-xs text-slate-500 mono">Architecture & Software</div>
                    </div>
                    <div class="relative z-10 text-xs text-slate-400 mono">
                        <p>Ali Veli</p>
                        <p>Lead Architect</p>
                        <p class="mt-2 text-blue-400">ali@fi-le.studio</p>
                    </div>
                    <div class="absolute bottom-4 right-4 w-8 h-8 border border-slate-700 rounded flex items-center justify-center">
                        <div class="w-4 h-4 bg-blue-500/20 rounded-sm"></div>
                    </div>
                </div>

                <!-- Letterhead -->
                <div class="logo-card bg-white rounded-xl p-8 aspect-[3/2] flex flex-col relative overflow-hidden md:col-span-2">
                    <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-600 to-cyan-500"></div>
                    <div class="flex justify-between items-start mb-12">
                        <div class="text-3xl font-bold text-slate-900 tracking-tighter">Fi/le</div>
                        <div class="text-xs text-slate-400 mono">Tarih: 2026-03-25</div>
                    </div>
                    <div class="flex-1 space-y-2">
                        <div class="h-2 bg-slate-200 rounded w-3/4"></div>
                        <div class="h-2 bg-slate-200 rounded w-full"></div>
                        <div class="h-2 bg-slate-200 rounded w-5/6"></div>
                        <div class="h-2 bg-slate-200 rounded w-4/6"></div>
                    </div>
                    <div class="mt-8 flex gap-4">
                        <div class="w-20 h-20 border-2 border-slate-200 rounded-lg flex items-center justify-center text-slate-300 text-xs mono">QR</div>
                        <div class="text-xs text-slate-400 mono self-end">
                            Fi/le Mimarlık Yazılım A.Ş.<br>
                            İstanbul, Türkiye
                        </div>
                    </div>
                </div>

                <!-- Digital -->
                <div class="logo-card bg-slate-950 border border-slate-800 rounded-xl p-4 aspect-video md:col-span-3 relative overflow-hidden">
                    <div class="absolute inset-0 blueprint-grid opacity-20"></div>
                    <div class="relative z-10 flex items-center justify-between h-full px-8">
                        <div class="flex items-center gap-4">
                            <div class="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-xl mono">F/l</div>
                            <div>
                                <div class="font-bold text-lg">Fi/le Dashboard</div>
                                <div class="text-xs text-slate-500 mono">v2.4.0-stable</div>
                            </div>
                        </div>
                        <div class="flex gap-4 text-xs mono">
                            <span class="px-3 py-1 rounded-full bg-green-500/10 text-green-400 border border-green-500/20">● Online</span>
                            <span class="px-3 py-1 rounded-full bg-slate-800 text-slate-400">Projects: 24</span>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Footer -->
        <footer class="border-t border-slate-800 pt-12 text-center">
            <div class="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-slate-900 border border-slate-800 mb-6">
                <span class="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
                <span class="text-sm mono text-slate-400">Design System Ready</span>
            </div>
            <p class="text-slate-500 text-sm">
                Fi/le Brand Identity ©️ 2026<br>
                Mimarlık ve Yazılımın Kesişimi
            </p>
        </footer>

    </main>

    <script>
        function switchTab(tab) {
            // Hide all contents
            document.getElementById('content-primary').classList.add('hidden');
            document.getElementById('content-icon').classList.add('hidden');
            document.getElementById('content-mono').classList.add('hidden');
            
            // Remove active classes
            document.getElementById('tab-primary').classList.remove('tab-active');
            document.getElementById('tab-primary').classList.add('text-slate-400');
            document.getElementById('tab-icon').classList.remove('tab-active');
            document.getElementById('tab-icon').classList.add('text-slate-400');
            document.getElementById('tab-mono').classList.remove('tab-active');
            document.getElementById('tab-mono').classList.add('text-slate-400');
            
            // Show selected content
            document.getElementById('content-' + tab).classList.remove('hidden');
            
            // Add active class to selected tab
            const activeTab = document.getElementById('tab-' + tab);
            activeTab.classList.add('tab-active');
            activeTab.classList.remove('text-slate-400');
            
            // Re-trigger animations
            const lines = document.querySelectorAll('.blueprint-line');
            lines.forEach(line => {
                line.style.animation = 'none';
                line.offsetHeight; // Trigger reflow
                line.style.animation = 'drawLine 3s ease-out forwards';
            });
        }

        // Glitch effect randomization
        setInterval(() => {
            const glitch = document.querySelector('.glitch');
            if (glitch && Math.random() > 0.9) {
                glitch.style.animation = 'none';
                setTimeout(() => {
                    glitch.style.animation = '';
                }, 100);
            }
        }, 3000);
    </script>
</body>
</html>
