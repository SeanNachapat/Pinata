"use client";

import React, { useState, useEffect } from "react";
import { 
  Activity, 
  Check, 
  Copy, 
  ArrowRight, 
  Terminal, 
  Settings, 
  Zap, 
  Cpu, 
  Layers
} from "lucide-react";

// ----------------- CONFIGURATIONS -----------------

const DEVICE_CONFIGS = {
  IndustrialMotor: {
    title: "Industrial Motor",
    type: "IndustrialMotor",
    description: "Simulates a manufacturing motor tracking rotational speed, housing temperature, electric draw, and physical vibrations.",
    baseValues: { RPM: 1500, Temperature: 45.0, Current: 10.0 },
    metrics: [
      { key: "RPM", label: "Rotational Speed", unit: "RPM" },
      { key: "Temperature", label: "Casing Temperature", unit: "°C" },
      { key: "Current", label: "Current Amperage", unit: "A" }
    ],
    anomalies: [
      { type: "bearing_wear", label: "🚨 Bearing Wear", desc: "Progressive bearing decay: increases vibration noise, raises power draw, spikes motor casing temp." },
      { type: "mechanical_jam", label: "🔥 Mechanical Jam", desc: "Rotor lock anomaly: RPM drops to 0 immediately, amperage draws spike, thermal lock is engaged." }
    ]
  },
  WindTurbine: {
    title: "Wind Turbine",
    type: "WindTurbine",
    description: "Simulates a utility-scale wind power turbine generating electricity, showing wind dynamics and mechanical gear ratios.",
    baseValues: { WindSpeed: 12.0, RotorRPM: 18.0, PowerOutput: 1500.0 },
    metrics: [
      { key: "WindSpeed", label: "Wind Speed", unit: "m/s" },
      { key: "RotorRPM", label: "Rotor Speed", unit: "RPM" },
      { key: "PowerOutput", label: "Power Output", unit: "kW" }
    ],
    anomalies: [
      { type: "blade_imbalance", label: "❄️ Blade Imbalance", desc: "Ice/crack dynamic load: introduces high cyclic vibration, drops overall power output, slows rotation." },
      { type: "gearbox_slippage", label: "⚙️ Gearbox Slippage", desc: "Friction breakdown: rotor speed spikes due to lack of resistance, generator output collapses." }
    ]
  },
  SmartHVAC: {
    title: "Commercial HVAC",
    type: "SmartHVAC",
    description: "Simulates building climate loops managing thermal exchanges, compressor pressures, and electricity loads.",
    baseValues: { RoomTemp: 24.5, CompressorPressure: 120.0, PowerLoad: 3.5 },
    metrics: [
      { key: "RoomTemp", label: "Room Temperature", unit: "°C" },
      { key: "CompressorPressure", label: "Compressor Pressure", unit: "PSI" },
      { key: "PowerLoad", label: "Electricity Load", unit: "kW" }
    ],
    anomalies: [
      { type: "refrigerant_leak", label: "💧 Refrigerant Leak", desc: "Coolant system rupture: pressure collapses, room cooling breaks down, room temp climbs steadily." },
      { type: "fan_failure", label: "💨 Fan Failure", desc: "Condenser fan failure: pressure shoots to critical safety lines, casing vibration spikes." }
    ]
  }
};

const CODE_EXAMPLES = {
  python: `from dummio import Server
from dummio.devices import IndustrialMotor
import asyncio

async def main():
    # 1. Spin up an Industrial Motor preset
    motor = IndustrialMotor(start_test_broker=True)
    
    # 2. Expose the REST/WebSocket API and start streaming
    server = Server(device=motor, host="0.0.0.0", port=8000)
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())`,
  curl: `# Inject a 60-second bearing wear failure
curl -X POST http://localhost:8000/api/inject \\
     -H "Content-Type: application/json" \\
     -d '{"anomaly_type": "bearing_wear", "duration_seconds": 60, "intensity": 1.5}'

# Clear active failures
curl -X POST http://localhost:8000/api/clear`,
  javascript: `// Connect to Dummio WebSocket stream
const ws = new WebSocket("ws://localhost:8000/ws");

ws.onmessage = (event) => {
  const reading = JSON.parse(event.data);
  console.log("Device ID:", reading.device_id);
  console.log("Sensors:", reading.sensors);
  console.log("Anomaly Flag:", reading.anomaly); // 0 or 1
};`
};

export default function LandingPage() {
  const [deviceKey, setDeviceKey] = useState<keyof typeof DEVICE_CONFIGS>("IndustrialMotor");
  const [ambientWear, setAmbientWear] = useState<number>(0);
  const [anomalySeverity, setAnomalySeverity] = useState<number>(1.0);
  const [anomalyDuration, setAnomalyDuration] = useState<number>(30);
  const [isInfinite, setIsInfinite] = useState<boolean>(false);
  const [activeAnomaly, setActiveAnomaly] = useState<string | null>(null);
  const [anomalyTimeRemaining, setAnomalyTimeRemaining] = useState<number | null>(null);
  
  // Simulation Values State
  const [metricsValues, setMetricsValues] = useState<Record<string, number>>({});
  const [vibrationVal, setVibrationVal] = useState<number>(0.1);
  const [metricsDeltas, setMetricsDeltas] = useState<Record<string, "up" | "down" | "flat">>({});
  const [chartData, setChartData] = useState<number[]>(Array(60).fill(50));
  const [logPackets, setLogPackets] = useState<string[]>([]);
  const [copiedState, setCopiedState] = useState<string | null>(null);
  const [activeCodeTab, setActiveCodeTab] = useState<keyof typeof CODE_EXAMPLES>("python");

  // Animation frame ticks
  const [animFrame, setAnimFrame] = useState<number>(0);
  
  const config = DEVICE_CONFIGS[deviceKey];

  // Calculate dynamic animation speed based on telemetry
  const getAnimDelay = () => {
    if (deviceKey === "IndustrialMotor") {
      if (activeAnomaly === "mechanical_jam") return null;
      const rpm = metricsValues["RPM"] || 1500;
      return rpm > 0 ? Math.max(40, Math.min(250, 120000 / rpm)) : null;
    }
    if (deviceKey === "WindTurbine") {
      const rpm = metricsValues["RotorRPM"] || 18.0;
      return rpm > 0 ? Math.max(40, Math.min(300, 1800 / rpm)) : null;
    }
    if (deviceKey === "SmartHVAC") {
      if (activeAnomaly === "fan_failure") return null;
      return 80; // Fast and smooth constant speed
    }
    return 100;
  };

  const animDelay = getAnimDelay();

  // ----------------- ANIMATION FRAME TIMERS -----------------
  useEffect(() => {
    if (animDelay === null) return;
    const animInterval = setInterval(() => {
      setAnimFrame(prev => (prev + 1) % 8);
    }, animDelay);
    return () => clearInterval(animInterval);
  }, [animDelay]);

  // ----------------- SIMULATION ENGINE (REACT CLIENT-SIDE) -----------------
  
  useEffect(() => {
    // Reset values on device swap
    const base = config.baseValues as any;
    const initialValues: Record<string, number> = {};
    Object.keys(base).forEach((key) => {
      initialValues[key] = base[key];
    });
    setMetricsValues(initialValues);
    
    let defaultVib = 0.1;
    if (deviceKey === "WindTurbine") defaultVib = 0.15;
    if (deviceKey === "SmartHVAC") defaultVib = 0.02;
    setVibrationVal(defaultVib);
    
    setChartData(Array(60).fill(50));
    setLogPackets([]);
    setActiveAnomaly(null);
    setAnomalyTimeRemaining(null);
  }, [deviceKey]);

  useEffect(() => {
    const interval = setInterval(() => {
      // 1. Manage anomaly countdown timer
      if (activeAnomaly && anomalyTimeRemaining !== null) {
        if (anomalyTimeRemaining <= 1) {
          setActiveAnomaly(null);
          setAnomalyTimeRemaining(null);
        } else {
          setAnomalyTimeRemaining(prev => (prev !== null ? prev - 1 : null));
        }
      }

      // 2. Generate physics-based readings
      const base = config.baseValues as any;
      const nextValues: Record<string, number> = {};
      const nextDeltas: Record<string, "up" | "down" | "flat"> = {};
      const noise = () => (Math.random() - 0.5);
      
      const wearCoeff = ambientWear / 100.0;
      let baseVib = 0.1;
      if (deviceKey === "WindTurbine") baseVib = 0.15;
      if (deviceKey === "SmartHVAC") baseVib = 0.02;

      let calculatedVib = baseVib + wearCoeff * 0.15 + Math.random() * 0.02;

      if (deviceKey === "IndustrialMotor") {
        // Motor model
        let rpm = base.RPM + noise() * 10 - wearCoeff * 15;
        let temp = base.Temperature + noise() * 0.5 + wearCoeff * 5.0;
        let current = base.Current + noise() * 0.3 + wearCoeff * 1.5;

        // Apply anomalies
        if (activeAnomaly === "bearing_wear") {
          calculatedVib += 0.8 * anomalySeverity + Math.random() * 0.2;
          temp += 12 * anomalySeverity;
          current += 4 * anomalySeverity;
          rpm -= 80 * anomalySeverity;
        } else if (activeAnomaly === "mechanical_jam") {
          rpm = 0.0;
          calculatedVib = Math.random() * 0.01;
          current = 48.0 + noise() * 0.8;
          temp += 22 * anomalySeverity;
        }

        nextValues["RPM"] = Math.round(rpm * 100) / 100;
        nextValues["Temperature"] = Math.round(temp * 100) / 100;
        nextValues["Current"] = Math.round(current * 100) / 100;

      } else if (deviceKey === "WindTurbine") {
        // Turbine model
        let wind = base.WindSpeed + noise() * 0.8;
        let powerRatio = Math.pow(wind / 12.0, 3);
        let rpm = wind * 1.5 + noise() * 0.15;
        let power = Math.max(0.0, powerRatio * base.PowerOutput + noise() * 15);
        let temp = base.GeneratorTemp + (power / 1000.0) * 8.0 + noise() * 0.2;

        if (activeAnomaly === "blade_imbalance") {
          calculatedVib += 1.2 * anomalySeverity + Math.random() * 0.1;
          power *= 0.82;
          rpm *= 0.88;
        } else if (activeAnomaly === "gearbox_slippage") {
          rpm = Math.max(rpm + 12 * anomalySeverity, 35);
          power *= 0.3;
          temp += 32 * anomalySeverity;
          calculatedVib += 0.5 * anomalySeverity;
        }

        nextValues["WindSpeed"] = Math.round(wind * 100) / 100;
        nextValues["RotorRPM"] = Math.round(rpm * 100) / 100;
        nextValues["PowerOutput"] = Math.round(power * 100) / 100;
        nextValues["GeneratorTemp"] = Math.round(temp * 100) / 100;

      } else if (deviceKey === "SmartHVAC") {
        // HVAC model
        let roomTemp = base.RoomTemp + noise() * 0.1 + wearCoeff * 1.2;
        let pressure = base.CompressorPressure + noise() * 1.5;
        let load = base.PowerLoad + noise() * 0.05 + wearCoeff * 0.4;

        if (activeAnomaly === "refrigerant_leak") {
          pressure = Math.max(12.0, pressure - 78 * anomalySeverity);
          roomTemp += 3.2 * anomalySeverity;
          load = 1.1 + noise() * 0.05;
        } else if (activeAnomaly === "fan_failure") {
          pressure += 92 * anomalySeverity;
          load = base.PowerLoad * (1.15 + 0.3 * anomalySeverity);
          roomTemp += 1.8 * anomalySeverity;
          calculatedVib += 0.45 * anomalySeverity;
        }

        nextValues["RoomTemp"] = Math.round(roomTemp * 100) / 100;
        nextValues["CompressorPressure"] = Math.round(pressure * 100) / 100;
        nextValues["PowerLoad"] = Math.round(load * 100) / 100;
      }

      setVibrationVal(Math.round(calculatedVib * 10000) / 10000);

      // Compute deltas
      Object.keys(nextValues).forEach((key) => {
        const curr = nextValues[key];
        const prev = metricsValues[key] || curr;
        if (curr > prev) nextDeltas[key] = "up";
        else if (curr < prev) nextDeltas[key] = "down";
        else nextDeltas[key] = "flat";
      });
      setMetricsDeltas(nextDeltas);
      setMetricsValues(nextValues);

      // 3. Append to chart history (Primary metric scaled to 0-100)
      let primaryPercent = 50;
      if (deviceKey === "IndustrialMotor") {
        primaryPercent = ((nextValues["RPM"] || 1500) / 3000) * 100;
      } else if (deviceKey === "WindTurbine") {
        primaryPercent = ((nextValues["PowerOutput"] || 1500) / 2800) * 100;
      } else if (deviceKey === "SmartHVAC") {
        primaryPercent = ((nextValues["CompressorPressure"] || 120) / 250) * 100;
      }
      primaryPercent = Math.min(100, Math.max(0, primaryPercent));

      setChartData(prev => {
        const next = [...prev.slice(1), primaryPercent];
        return next;
      });

      // 4. Create WebSocket JSON packet log
      const packet = {
        timestamp: new Date().toISOString(),
        device_id: "dev-virtual-iot-d1",
        preset: config.type,
        anomaly: activeAnomaly ? 1 : 0,
        anomaly_type: activeAnomaly || null,
        sensors: {
          ...nextValues,
          VibrationX: Math.round((calculatedVib + (Math.random() - 0.5) * 0.02) * 10000) / 10000,
          VibrationY: Math.round((calculatedVib + (Math.random() - 0.5) * 0.02) * 10000) / 10000,
          VibrationZ: Math.round((calculatedVib + (Math.random() - 0.5) * 0.02) * 10000) / 10000
        }
      };

      setLogPackets(prev => {
        const next = [JSON.stringify(packet, null, 2), ...prev];
        return next.slice(0, 5);
      });

    }, 400);

    return () => clearInterval(interval);
  }, [deviceKey, activeAnomaly, anomalyTimeRemaining, ambientWear, anomalySeverity, metricsValues]);

  // ----------------- HANDLERS -----------------

  const triggerAnomaly = (type: string) => {
    setActiveAnomaly(type);
    if (isInfinite) {
      setAnomalyTimeRemaining(null);
    } else {
      setAnomalyTimeRemaining(anomalyDuration);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedState(id);
    setTimeout(() => setCopiedState(null), 2000);
  };

  // ----------------- REAL-TIME ASCII RENDERING -----------------

  const getActiveASCII = () => {
    const isJam = activeAnomaly === "mechanical_jam";
    const isImbalance = activeAnomaly === "blade_imbalance";
    const isSlippage = activeAnomaly === "gearbox_slippage";
    const isLeak = activeAnomaly === "refrigerant_leak";
    const isFanFail = activeAnomaly === "fan_failure";

    const cleanASCII = (str: string) => {
      // Remove leading and trailing newlines, but preserve spaces on actual content lines!
      return str.replace(/^\r?\n+/, '').replace(/\r?\n+$/, '');
    };

    if (deviceKey === "IndustrialMotor") {
      const fanChars = ["|", "/", "-", "\\", "|", "/", "-", "\\"];
      const shaftChars = ["|", "/", "-", "\\", "|", "/", "-", "\\"];
      const fan = isJam ? "X" : fanChars[animFrame % 8];
      const shaft = isJam ? "X" : shaftChars[animFrame % 8];
      const statusText = isJam 
        ? "⚠️ ERROR: ROTOR JAMMED // THERMAL LOCK DETECTED" 
        : activeAnomaly === "bearing_wear"
        ? "⚡ WARNING: HIGH BEARING VIBRATION MEASURED"
        : `⚙️ ACTIVE CORE [RPM: ${metricsValues["RPM"] || 1500}]`;

      return cleanASCII(`
         ______       ___________________________________________
       //      \\\\    /                                           \\
      ||   ${fan}    ||  |   [|||||||||||||||||||||||||||||||||||]     |====.        .-.
      ||  |  |   ||  |   [         INDUSTRIAL MOTOR          ]     |    |=======( ${shaft} )=======> SHAFT OUT
       \\\\______//   |   [ ${statusText.padEnd(39)} ]     |===='        '-'
                     \\___________________________________________/
                            ||                           ||
                    =================================================== [MOUNT PLATE]
      `);
    }

    if (deviceKey === "WindTurbine") {
      const blades = [
        // Frame 0: 0, 120, 240 deg (vertical UP, down-right, down-left)
        `                     |
                     |
                     |
                 .===O===.
                / [ GEN ] \\\\
               |           |
              /             \\\\
             /               \\\\
            /                 \\\\`,
        // Frame 1: 15, 135, 255 deg
        `                      \\\\
                       \\\\
                        \\\\
             ____.===O===.
                / [ GEN ] \\\\
               |     |     |
                     |      
                     |       
                     |        `,
        // Frame 2: 30, 150, 270 deg (top-right, bottom-right, horizontal left)
        `                        \\\\\\\\
                         \\\\\\\\
                          \\\\\\\\
          _______.===O===.
                / [ GEN ] \\\\
               |     \\\\     |
                      \\\\     
                       \\\\     
                              `,
        // Frame 3: 45, 165, 285 deg (diagonal top-right, bottom-right-steep, up-left)
        `                            \\\\
                             \\\\
          \\\\                  \\\\
           \\\\    .===O===.
                / [ GEN ] \\\\
               |     \\\\     |
                      \\\\     
                      |      
                      |       `,
        // Frame 4: 60, 180, 300 deg (flatter top-right, vertical down, up-left-steep)
        `              \\\\
               \\\\
                \\\\  .===O===. ______
                / [ GEN ] \\\\
               |     |     |
                     |
                     |
                     |
                              `,
        // Frame 5: 75, 195, 315 deg (almost horizontal right, down-left, diagonal up-left)
        `         \\\\
          \\\\
           \\\\    .===O===. ________
                / [ GEN ] \\\\
               |           |
              /
             /
            /
                              `,
        // Frame 6: 90, 210, 330 deg (horizontal right, down-left-flatter, up-left-flatter)
        `          \\\\
           \\\\
            \\\\    .===O===. _________
                / [ GEN ] \\\\
               |           |
              /             \\\\
             /
            /
                              `,
        // Frame 7: 105, 225, 345 deg (bottom-right, down-left-steep, almost vertical UP)
        `                     |
                     |
                     |
                 .===O===.
                / [ GEN ] \\\\
               |           \\\\
              /             \\\\
             /
            /`
      ];

      const currentBlade = cleanASCII(blades[animFrame % 8]);
      const statusText = isImbalance 
        ? "⚠️ STATE: HEAVY ROTOR ASYMMETRY LOAD"
        : isSlippage
        ? "⚠️ STATE: GEAR FRICTION OVERHEAT BREAKDOWN"
        : `⚡ STATE: GENERATING DYNAMIC POWER [${metricsValues["PowerOutput"] || 1200} kW]`;

      return cleanASCII(`
${currentBlade}
                 ||     ||   ${statusText}
                 ||     ||
             ==========================================
      `);
    }

    if (deviceKey === "SmartHVAC") {
      const fanChars = ["(|)", "(/)", "(-)", "(\\)"];
      const fan = isFanFail ? "(!)" : fanChars[animFrame % 4];
      const statusText = isFanFail
        ? "⚠️ STATE: FANS LOCKOUT // DANGEROUS CASING PSI"
        : isLeak
        ? "⚠️ STATE: REFRIGERANT DISCHARGE IN PROGRESS"
        : "✔ STATE: HEAT EXCHANGE PIPELINES FUNCTIONAL";

      return cleanASCII(`
       ___________________________________________
      /                                           \\
     |   [ HVAC UNIT CORE ]                       |
     |   .------------------------------------.   |
     |   |   ( )            ( )          ( )  |   |====► EXHAUST AIR
     |   |  [${fan}]          [${fan}]          [${fan}]  |   |
     |   '------------------------------------'   |   ${statusText}
      \\___________________________________________/
      `);
    }

    return "";
  };

  return (
    <div className="min-h-screen bg-[#f4f4f6] text-black selection:bg-black selection:text-white p-0 md:p-8 font-sans flex flex-col items-center justify-start">
      
      {/* ----------------- PHYSICAL CANVAS WORKSPACE ----------------- */}
      <div className="w-full max-w-[1300px] bg-white border border-black md:border-2 shadow-2xl flex flex-col overflow-hidden relative">
        
        {/* TOP STATUS BAR */}
        <header className="border-b border-black flex flex-row justify-between items-center text-[10px] font-mono uppercase bg-[#fcfcfd]">
          <div className="px-4 py-2.5 border-r border-black font-bold flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-black animate-pulse" />
            DUMMIO V.01
          </div>
          <div className="px-4 py-2.5 font-semibold flex items-center gap-1">
            {activeAnomaly ? (
              <span className="text-red-600 bg-red-50 px-2 py-0.5 border border-red-400 font-bold animate-pulse">
                ⚠ ANOMALY ACTIVE
              </span>
            ) : (
              <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 border border-emerald-400">
                ● ONLINE
              </span>
            )}
          </div>
        </header>

        {/* HERO TITLE SECTION */}
        <section className="px-6 py-8 border-b border-black">
          <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tighter uppercase text-black leading-none mb-2">
            D1 VIRTUAL HARDWARE
          </h1>
          <p className="text-xs font-mono text-gray-500 leading-normal max-w-2xl mb-5">
            Open-source IoT device emulator with physics-based telemetry and failure injection APIs.
          </p>

          {/* INSTALL + STATS + CTA */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            {/* pip install */}
            <div className="flex items-center gap-2 border border-black px-3 py-2 bg-gray-50 font-mono text-[11px]">
              <Terminal className="w-3.5 h-3.5 text-black flex-shrink-0" />
              <code className="text-black font-bold">pip install dummio</code>
              <button 
                onClick={() => copyToClipboard("pip install dummio", "pip")}
                className="ml-1 w-6 h-6 flex items-center justify-center border border-black bg-white hover:bg-black hover:text-white transition-all flex-shrink-0"
              >
                {copiedState === "pip" ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
              </button>
            </div>

            {/* Quick stats */}
            <div className="flex items-center gap-3 font-mono text-[10px] text-gray-500 uppercase">
              <span className="border border-gray-300 px-2 py-1.5">Python 3.8+</span>
              <span className="border border-gray-300 px-2 py-1.5">MIT License</span>
              <span className="border border-gray-300 px-2 py-1.5">Zero Hardware</span>
            </div>

            {/* GitHub CTA */}
            <a 
              href="https://github.com/SeanNachapat/Dummio" 
              target="_blank" 
              rel="noreferrer" 
              className="flex items-center gap-1.5 border border-black px-3 py-2 bg-black text-white font-mono text-[10px] font-bold uppercase hover:bg-white hover:text-black transition-all"
            >
              <svg className="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24">
                <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.46-1.16-1.11-1.47-1.11-1.47-.9-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.9 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0012 2z" />
              </svg>
              <span>View on GitHub</span>
            </a>
          </div>
        </section>

        {/* UTILITY BAR PRESENTS SWITCHER */}
        <section className="border-b border-black grid grid-cols-3 text-center font-mono text-[11px] sm:text-xs bg-[#fafafa]">
          <button 
            onClick={() => setDeviceKey("IndustrialMotor")}
            className={`py-3 border-r border-black font-bold uppercase transition-all flex items-center justify-center gap-1.5 ${
              deviceKey === "IndustrialMotor" 
                ? "bg-black text-white" 
                : "text-gray-500 hover:bg-gray-100"
            }`}
          >
            <span>[01 // MOTOR PRES]</span>
          </button>
          <button 
            onClick={() => setDeviceKey("WindTurbine")}
            className={`py-3 border-r border-black font-bold uppercase transition-all flex items-center justify-center gap-1.5 ${
              deviceKey === "WindTurbine" 
                ? "bg-black text-white" 
                : "text-gray-500 hover:bg-gray-100"
            }`}
          >
            <span>[02 // TURBINE PRES]</span>
          </button>
          <button 
            onClick={() => setDeviceKey("SmartHVAC")}
            className={`py-3 font-bold uppercase transition-all flex items-center justify-center gap-1.5 ${
              deviceKey === "SmartHVAC" 
                ? "bg-black text-white" 
                : "text-gray-500 hover:bg-gray-100"
            }`}
          >
            <span>[03 // HVAC PRES]</span>
          </button>
        </section>

        {/* CORE EMULATOR INTERFACE */}
        <main className="grid grid-cols-1 md:grid-cols-12">
          
          {/* LEFT COLUMN: ASCII SCREEN & CONTROLS */}
          <div className="col-span-12 md:col-span-6 border-b md:border-b-0 md:border-r border-black p-6 flex flex-col justify-start bg-white">
            {/* REAL-TIME DYNAMIC ASCII SCREEN */}
            <div className="w-full bg-gray-50 border border-black p-4 font-mono text-[9px] sm:text-[11px] overflow-x-auto text-black leading-tight select-none mb-6 min-h-[170px] flex items-center justify-start border-double border-4">
              <pre className="m-0 font-mono font-bold leading-normal">{getActiveASCII()}</pre>
            </div>

            <hr className="border-black mb-4" />

            {/* Ambient Wear Slider */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] font-mono uppercase font-bold text-black">Wear</span>
                <span className="text-[10px] font-mono font-bold text-black">{ambientWear}%</span>
              </div>
              <input 
                type="range" 
                min="0" 
                max="100" 
                value={ambientWear}
                onChange={(e) => setAmbientWear(parseInt(e.target.value))}
                className="w-full accent-black cursor-pointer"
              />
            </div>

            <hr className="border-black mb-4 mt-4" />

            {/* Failure Injection Block */}
            <div className="mb-4">
              
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] font-mono text-gray-600 uppercase">Intensity Scale</span>
                    <span className="text-[10px] font-mono font-bold text-black">{anomalySeverity}x</span>
                  </div>
                  <input 
                    type="range" 
                    min="0.2" 
                    max="3.0" 
                    step="0.1"
                    value={anomalySeverity}
                    onChange={(e) => setAnomalySeverity(parseFloat(e.target.value))}
                    className="w-full accent-black cursor-pointer"
                  />
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] font-mono text-gray-600 uppercase">Timer Frame</span>
                    <span className="text-[10px] font-mono font-bold text-black">{isInfinite ? "IND" : `${anomalyDuration}s`}</span>
                  </div>
                  <input 
                    type="range" 
                    min="5" 
                    max="120" 
                    step="5"
                    disabled={isInfinite}
                    value={anomalyDuration}
                    onChange={(e) => setAnomalyDuration(parseInt(e.target.value))}
                    className="w-full accent-black cursor-pointer disabled:opacity-30"
                  />
                </div>
              </div>

              <label className="flex items-center gap-2 cursor-pointer mb-6 select-none font-mono text-[10px]">
                <input 
                  type="checkbox" 
                  checked={isInfinite}
                  onChange={(e) => setIsInfinite(e.target.checked)}
                  className="w-3.5 h-3.5 border border-black rounded-none appearance-none checked:bg-black cursor-pointer relative checked:before:content-['✓'] checked:before:text-white checked:before:absolute checked:before:top-[-2px] checked:before:left-[2px] checked:before:font-bold"
                />
                <span className="text-gray-700 uppercase">Emulate anomalous state indefinitely</span>
              </label>

              <div className="grid grid-cols-2 gap-2 mb-4">
                {config.anomalies.map((anom) => {
                  const isActive = activeAnomaly === anom.type;
                  return (
                    <button 
                      key={anom.type}
                      onClick={() => triggerAnomaly(anom.type)}
                      className={`px-3 py-2 text-center border transition-all font-mono ${
                        isActive 
                          ? "bg-red-500 text-white border-black" 
                          : "bg-white text-black border-black hover:bg-gray-50"
                      }`}
                    >
                      <span className="font-bold text-[10px] uppercase">
                        {isActive ? `🚨 ACTIVE` : `[ ${anom.label.replace(/🚨|🔥|❄️|⚙️|💧|💨/g, '').trim().toUpperCase()} ]`}
                      </span>
                    </button>
                  );
                })}
              </div>

              <button 
                onClick={() => {
                  setActiveAnomaly(null);
                  setAnomalyTimeRemaining(null);
                }}
                className="w-full h-9 text-[10px] font-mono font-bold uppercase tracking-wider border border-black bg-black text-white hover:bg-white hover:text-black transition-all flex items-center justify-center gap-1"
              >
                ✔ RESET
              </button>
            </div>
          </div>

          {/* RIGHT COLUMN: TELEMETRY & OSCILLOSCOPE */}
          <div className="col-span-12 md:col-span-6 p-6 flex flex-col justify-start bg-white">

            {/* SENSORS EXPLORES TABLE */}
            <div className="w-full border border-black mb-6">
              <div className="grid grid-cols-4 bg-gray-50 border-b border-black text-[10px] font-mono uppercase font-bold text-gray-600 px-3 py-2 text-left">
                <div>SENSOR</div>
                <div>PARAMETER</div>
                <div>VALUE</div>
                <div className="text-right">STATUS</div>
              </div>

              {/* Row 1 */}
              <div className="grid grid-cols-4 border-b border-black text-[11px] font-mono px-3 py-2.5 items-center">
                <div className="font-bold">{config.metrics[0].key}</div>
                <div className="text-gray-500 text-[10px]">{config.metrics[0].label}</div>
                <div className="font-bold">{metricsValues[config.metrics[0].key] || 0} {config.metrics[0].unit}</div>
                <div className="text-right">
                  {metricsDeltas[config.metrics[0].key] === "up" && <span className="text-black font-bold">▲ ASC</span>}
                  {metricsDeltas[config.metrics[0].key] === "down" && <span className="text-black font-bold">▼ DSC</span>}
                  {metricsDeltas[config.metrics[0].key] === "flat" && <span className="text-gray-400">■ STB</span>}
                </div>
              </div>

              {/* Row 2 */}
              <div className="grid grid-cols-4 border-b border-black text-[11px] font-mono px-3 py-2.5 items-center">
                <div className="font-bold">{config.metrics[1].key}</div>
                <div className="text-gray-500 text-[10px]">{config.metrics[1].label}</div>
                <div className="font-bold">{metricsValues[config.metrics[1].key] || 0} {config.metrics[1].unit}</div>
                <div className="text-right">
                  {metricsDeltas[config.metrics[1].key] === "up" && <span className="text-black font-bold">▲ ASC</span>}
                  {metricsDeltas[config.metrics[1].key] === "down" && <span className="text-black font-bold">▼ DSC</span>}
                  {metricsDeltas[config.metrics[1].key] === "flat" && <span className="text-gray-400">■ STB</span>}
                </div>
              </div>

              {/* Row 3 */}
              <div className="grid grid-cols-4 border-b border-black text-[11px] font-mono px-3 py-2.5 items-center">
                <div className="font-bold">{config.metrics[2].key}</div>
                <div className="text-gray-500 text-[10px]">{config.metrics[2].label}</div>
                <div className="font-bold">{metricsValues[config.metrics[2].key] || 0} {config.metrics[2].unit}</div>
                <div className="text-right">
                  {metricsDeltas[config.metrics[2].key] === "up" && <span className="text-black font-bold">▲ ASC</span>}
                  {metricsDeltas[config.metrics[2].key] === "down" && <span className="text-black font-bold">▼ DSC</span>}
                  {metricsDeltas[config.metrics[2].key] === "flat" && <span className="text-gray-400">■ STB</span>}
                </div>
              </div>

              {/* Row 4 (Vibration) */}
              <div className="grid grid-cols-4 text-[11px] font-mono px-3 py-2.5 items-center">
                <div className="font-bold">Vibration</div>
                <div className="text-gray-500 text-[10px]">Overall G RMS</div>
                <div className="font-bold">{vibrationVal} G</div>
                <div className="text-right">
                  {vibrationVal > 0.4 ? (
                    <span className="text-red-600 bg-red-50 px-1 border border-red-300 font-bold animate-pulse text-[9px]">⚠️ EXTREME</span>
                  ) : (
                    <span className="text-emerald-700 bg-emerald-50 px-1 border border-emerald-300 text-[9px]">✔ STABLE</span>
                  )}
                </div>
              </div>
            </div>

            {/* LIVE OSCILLOSCOPE TIME SERIES */}
            <div className="border border-black p-3 bg-[#fcfcfd] flex flex-col mb-6">
              
              {/* Dot matrix grid background container */}
              <div className="h-[160px] border border-black relative overflow-hidden bg-white dot-matrix">
                
                {/* Horizontal line indicators */}
                <div className="absolute top-[40px] left-0 w-full border-t border-gray-200 border-dashed" />
                <div className="absolute top-[80px] left-0 w-full border-t border-gray-200 border-dashed" />
                <div className="absolute top-[120px] left-0 w-full border-t border-gray-200 border-dashed" />

                <svg className="absolute inset-0 w-full h-full" viewBox="0 0 300 160" preserveAspectRatio="none">
                  {/* Vector single-pixel solid curve path */}
                  {chartData.length > 1 && (
                    <path 
                      d={chartData.map((val, idx) => `${idx === 0 ? "M" : "L"} ${(idx / 59) * 300} ${160 - (val / 100) * 140}`).join(" ")}
                      fill="none"
                      stroke={activeAnomaly ? "#ef4444" : "#000000"}
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  )}
                </svg>

                {activeAnomaly && (
                  <div className="absolute top-2 right-2 text-[8px] font-mono bg-red-600 text-white px-2 py-0.5 border border-black font-bold animate-pulse">
                    ANOMALY OSCILLATION SIGNALS
                  </div>
                )}
              </div>
            </div>

            {/* WEBSOCKET PACKET LOG TICKER */}
            <div className="border border-black p-4 bg-[#fcfcfd] flex flex-col flex-1 min-h-[220px]">
              <div className="flex justify-between items-center mb-3">
                <span className="text-[10px] font-mono font-bold text-gray-500 uppercase flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-black" />
                  WSRAW_RECEIPT_FEED // WS://LOCALHOST:8000/WS
                </span>
                <span className="w-2.5 h-2.5 rounded-full bg-black animate-ping" />
              </div>

              <div className="flex-1 bg-white text-black rounded-none p-3.5 font-mono text-[9px] sm:text-[10px] overflow-y-auto max-h-[220px] border border-black shadow-inner">
                {logPackets.length > 0 ? (
                  <pre className="m-0 leading-relaxed whitespace-pre-wrap">{logPackets[0]}</pre>
                ) : (
                  <div className="h-full flex items-center justify-center text-gray-600 font-mono uppercase">
                    [ Waiting for device signal transmission... ]
                  </div>
                )}
              </div>
            </div>

          </div>
        </main>

        {/* ----------------- CORE PROTOCOL MARKETING FEATURE SET ----------------- */}
        <section className="border-t border-black grid grid-cols-1 md:grid-cols-3 bg-[#fafafa]">
          
          <div className="p-6 border-b md:border-b-0 md:border-r border-black flex flex-col">
            <div className="w-8 h-8 border border-black flex items-center justify-center bg-white text-black font-mono font-bold mb-4 text-xs">
              01
            </div>
            <h3 className="text-xs font-mono font-bold uppercase text-black mb-2 flex items-center gap-1">
              <Cpu className="w-4 h-4" />
              <span>Realism Emulators</span>
            </h3>
            <p className="text-[11px] font-mono text-gray-600 leading-normal">
              Instantly deploy highly realistic multivariable virtual hardware structures. Rotational metrics, heat transfers, electricity loads, and vibration equations resolve dynamically.
            </p>
          </div>

          <div className="p-6 border-b md:border-b-0 md:border-r border-black flex flex-col">
            <div className="w-8 h-8 border border-black flex items-center justify-center bg-white text-black font-mono font-bold mb-4 text-xs">
              02
            </div>
            <h3 className="text-xs font-mono font-bold uppercase text-black mb-2 flex items-center gap-1">
              <Layers className="w-4 h-4" />
              <span>Multi-Protocol Framework</span>
            </h3>
            <p className="text-[11px] font-mono text-gray-600 leading-normal">
              Stream live telemetry parameters over native WebSocket pipelines, publish payload maps to external MQTT brokers (e.g. Mosquitto), and script anomalies via JSON REST endpoints.
            </p>
          </div>

          <div className="p-6 flex flex-col">
            <div className="w-8 h-8 border border-black flex items-center justify-center bg-white text-black font-mono font-bold mb-4 text-xs">
              03
            </div>
            <h3 className="text-xs font-mono font-bold uppercase text-black mb-2 flex items-center gap-1">
              <Activity className="w-4 h-4" />
              <span>Ground Truth Data</span>
            </h3>
            <p className="text-[11px] font-mono text-gray-600 leading-normal">
              Every data feed emitted by the virtual hardware includes explicit binary labels (<code className="text-black bg-gray-150 px-1">anomaly: 0 | 1</code>) for instant train/validation loops in ML anomaly pipelines.
            </p>
          </div>

        </section>

        {/* ----------------- CODE INTEGRATION TABS DRAWER ----------------- */}
        <section id="code" className="border-t border-black bg-white">
          <div className="grid grid-cols-1 lg:grid-cols-12">
            
            {/* TABS DRAWER SELECTOR */}
            <div className="lg:col-span-5 border-b lg:border-b-0 lg:border-r border-black flex flex-col justify-start">
              <div className="px-6 py-4 border-b border-black font-mono text-xs font-bold bg-[#fafafa] uppercase">
                [ TECHNICAL CODE INTEGRATION OPTIONS ]
              </div>
              
              <div className="flex flex-col">
                <button 
                  onClick={() => setActiveCodeTab("python")}
                  className={`w-full p-4 border-b border-black text-left font-mono transition-all flex items-center justify-between ${
                    activeCodeTab === "python" 
                      ? "bg-black text-white" 
                      : "bg-white text-black hover:bg-gray-50"
                  }`}
                >
                  <div>
                    <h4 className="font-bold text-xs">01 // PYTHON ENGINE INITIALIZE</h4>
                    <p className={`text-[9px] mt-0.5 ${activeCodeTab === "python" ? "text-gray-300" : "text-gray-500"}`}>
                      Spin up a local mechanical physics emu with standard REST endpoints.
                    </p>
                  </div>
                  <ArrowRight className={`w-4 h-4 ${activeCodeTab === "python" ? "text-white" : "text-black"}`} />
                </button>

                <button 
                  onClick={() => setActiveCodeTab("curl")}
                  className={`w-full p-4 border-b border-black text-left font-mono transition-all flex items-center justify-between ${
                    activeCodeTab === "curl" 
                      ? "bg-black text-white" 
                      : "bg-white text-black hover:bg-gray-50"
                  }`}
                >
                  <div>
                    <h4 className="font-bold text-xs">02 // REST API INJECTOR cURL</h4>
                    <p className={`text-[9px] mt-0.5 ${activeCodeTab === "curl" ? "text-gray-300" : "text-gray-500"}`}>
                      Remotely inject scheduled failure models into active systems.
                    </p>
                  </div>
                  <ArrowRight className={`w-4 h-4 ${activeCodeTab === "curl" ? "text-white" : "text-black"}`} />
                </button>

                <button 
                  onClick={() => setActiveCodeTab("javascript")}
                  className={`w-full p-4 text-left font-mono transition-all flex items-center justify-between ${
                    activeCodeTab === "javascript" 
                      ? "bg-black text-white" 
                      : "bg-white text-black hover:bg-gray-50"
                  }`}
                >
                  <div>
                    <h4 className="font-bold text-xs">03 // WEBSOCKET CLIENT STREAM</h4>
                    <p className={`text-[9px] mt-0.5 ${activeCodeTab === "javascript" ? "text-gray-300" : "text-gray-500"}`}>
                      Stream raw state-vector dictionaries directly into web interfaces.
                    </p>
                  </div>
                  <ArrowRight className={`w-4 h-4 ${activeCodeTab === "javascript" ? "text-white" : "text-black"}`} />
                </button>
              </div>
            </div>

            {/* CODE OUTPUT PANEL */}
            <div className="lg:col-span-7 p-6 bg-[#fafafa] flex flex-col justify-start relative">
              <div className="absolute top-4 right-4 z-10">
                <button 
                  onClick={() => copyToClipboard(CODE_EXAMPLES[activeCodeTab], activeCodeTab)}
                  className="px-3 h-8 text-[10px] font-mono font-bold uppercase tracking-wider border border-black bg-white hover:bg-black hover:text-white transition-all flex items-center gap-1.5"
                >
                  {copiedState === activeCodeTab ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-600" />
                      <span>COPIED SUCCESSFULLY</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>COPY CODE CLIPBOARD</span>
                    </>
                  )}
                </button>
              </div>

              <div className="flex items-center gap-1.5 mb-4">
                <span className="w-2.5 h-2.5 rounded-full bg-black" />
                <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">
                  FILENAME: {activeCodeTab === "python" && "main.py"}
                  {activeCodeTab === "curl" && "trigger_failure.sh"}
                  {activeCodeTab === "javascript" && "websocket_subscriber.js"}
                </span>
              </div>

              <div className="bg-white text-black rounded-none p-5 font-mono text-[10px] sm:text-[11px] overflow-x-auto border border-black shadow-inner leading-normal max-h-[320px]">
                <pre className="m-0 leading-relaxed text-black">{CODE_EXAMPLES[activeCodeTab]}</pre>
              </div>
            </div>

          </div>
        </section>

        {/* ----------------- CORE UTILITY FOOTER ----------------- */}
        <footer className="border-t border-black px-6 py-6 bg-[#fcfcfd] flex flex-col sm:flex-row justify-between items-center gap-3 text-[10px] font-mono text-gray-500 uppercase">
          <div className="flex items-center gap-2">
            <Zap className="w-3.5 h-3.5 text-black" />
            <span className="font-bold text-black text-[11px]">DUMMIO</span>
            <span>— Open-source virtual IoT simulator</span>
          </div>
          
          <div>
            © {new Date().getFullYear()} MIT License
          </div>

          <a href="https://github.com/SeanNachapat/Dummio" target="_blank" rel="noreferrer" className="text-black font-bold hover:underline">
            github.com/SeanNachapat/Dummio
          </a>
        </footer>

      </div>
      
    </div>
  );
}
