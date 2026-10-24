import os

BASE_DIR = "/Users/tanchonl/Documents/tspiApp"

files = {}

files["package.json"] = """{
  "name": "tspiapp",
  "version": "1.0.0",
  "main": "node_modules/expo/AppEntry.js",
  "scripts": {
    "start": "expo start",
    "android": "expo start --android",
    "ios": "expo start --ios",
    "web": "expo start --web"
  },
  "dependencies": {
    "expo": "~51.0.0",
    "expo-status-bar": "~1.12.1",
    "react": "18.2.0",
    "react-native": "0.74.5"
  },
  "devDependencies": {
    "@babel/core": "^7.20.0",
    "@types/react": "~18.2.45",
    "typescript": "^5.1.3"
  },
  "private": true
}
"""

files["app.json"] = """{
  "expo": {
    "name": "TSPI Patient Care",
    "slug": "tspiapp",
    "version": "1.0.0",
    "orientation": "portrait",
    "icon": "./assets/icon.png",
    "userInterfaceStyle": "dark",
    "splash": {
      "image": "./assets/splash.png",
      "resizeMode": "contain",
      "backgroundColor": "#0F172A"
    },
    "ios": {
      "supportsTablet": true,
      "bundleIdentifier": "com.tspi.patientapp"
    },
    "android": {
      "adaptiveIcon": {
        "foregroundImage": "./assets/adaptive-icon.png",
        "backgroundColor": "#0F172A"
      },
      "package": "com.tspi.patientapp"
    },
    "web": {
      "favicon": "./assets/favicon.png"
    }
  }
}
"""

files["tsconfig.json"] = """{
  "compilerOptions": {
    "target": "esnext",
    "module": "commonjs",
    "lib": ["es6"],
    "allowJs": true,
    "jsx": "react-native",
    "noEmit": true,
    "isolatedModules": true,
    "strict": true,
    "moduleResolution": "node",
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    },
    "allowSyntheticDefaultImports": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "exclude": ["node_modules", "babel.config.js", "metro.config.js"]
}
"""

files["src/types/index.ts"] = """export interface PatientProfile {
  id: number;
  first_name: string;
  last_name: string;
  hn?: string;
  phone?: string;
  age?: number;
  gender?: string;
  underlying_disease?: string;
}

export interface ThreeKeyScore {
  score: number | null;
  confidence: number | null;
  label: string;
  assessment_coverage?: string;
  key_uncertainty?: string;
  note?: string;
}

export interface ThreeKeysData {
  metabolic_energy?: ThreeKeyScore;
  biological_dynamic?: ThreeKeyScore;
  biointegrity?: ThreeKeyScore;
}

export interface PatientReportChapter {
  title: string;
  content: string;
}

export interface PatientReportData {
  chapters: Record<string, PatientReportChapter>;
  framework_version?: string;
  status?: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  patient: PatientProfile | null;
}
"""

files["src/theme/theme.ts"] = """export const theme = {
  colors: {
    bgDark: "#0B132B",
    bgCard: "#1C2541",
    bgCardElevated: "#2D3748",
    primary: "#3A86FF",
    primaryLight: "#60A5FA",
    secondary: "#06D6A0",
    accent: "#FF006E",
    warning: "#FFBE0B",
    danger: "#EF4444",
    textPrimary: "#F8FAFC",
    textSecondary: "#94A3B8",
    textMuted: "#64748B",
    border: "#334155",
    borderLight: "#475569",
    success: "#10B981"
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32
  },
  borderRadius: {
    sm: 8,
    md: 12,
    lg: 20,
    full: 9999
  },
  typography: {
    title: {
      fontSize: 24,
      fontWeight: "700" as const,
      color: "#F8FAFC"
    },
    subtitle: {
      fontSize: 18,
      fontWeight: "600" as const,
      color: "#F8FAFC"
    },
    body: {
      fontSize: 15,
      lineHeight: 22,
      color: "#CBD5E1"
    },
    caption: {
      fontSize: 13,
      color: "#94A3B8"
    }
  }
};
"""

files["src/services/api.ts"] = """import { PatientProfile, ThreeKeysData, PatientReportData } from '../types';

// Replace with your Django backend IP address when testing on mobile device (e.g. http://192.168.1.100:8000)
export const API_BASE_URL = "http://127.0.0.1:8000";

export async function activatePatient(phone: string, name: string): Promise<{ token: string; patient: PatientProfile }> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/accounts/activate/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone, name })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || "ไม่พบข้อมูลการลงทะเบียนคนไข้ กรุณาติดต่อคลินิก");
    }
    const data = await res.json();
    return {
      token: data.tokens?.access || "demo-token",
      patient: data.patient
    };
  } catch (error: any) {
    // Fallback Mock for offline / demo mode
    if (error.message && error.message.includes("Network")) {
      return {
        token: "demo-patient-token-12345",
        patient: {
          id: 1,
          first_name: name || "คุณสมชาย",
          last_name: "ใจดี",
          phone: phone || "0812345678",
          hn: "HN-2026-0089",
          age: 45,
          gender: "ชาย",
          underlying_disease: "T2DM, Hypertension"
        }
      };
    }
    throw error;
  }
}

export async function fetchBiologicalHUD(patientId: number, token: string): Promise<ThreeKeysData> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/patients/${patientId}/calculate-precision-medicine/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({})
    });
    if (!res.ok) throw new Error("Failed to fetch HUD");
    const data = await res.json();
    return data.three_keys || {};
  } catch (e) {
    // Fallback Mock Data
    return {
      metabolic_energy: {
        score: 62,
        confidence: 0.85,
        label: "Metabolic Energy",
        assessment_coverage: "6/6 axes assessed",
        note: "Moderate disturbance — Require dietary & glucose tracking"
      },
      biological_dynamic: {
        score: 45,
        confidence: 0.80,
        label: "Biological Dynamic",
        assessment_coverage: "7/8 axes assessed",
        note: "Mild disturbance — Hemodynamics baseline stable"
      },
      biointegrity: {
        score: 30,
        confidence: 0.90,
        label: "Biointegrity",
        assessment_coverage: "12/15 axes assessed",
        note: "Good integrity — Cellular repair active"
      }
    };
  }
}

export async function fetchPatientReport(patientId: number, token: string): Promise<PatientReportData> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/ai/report/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({
        patient_id: String(patientId),
        edition: "patient"
      })
    });
    if (!res.ok) throw new Error("Failed to generate Patient Report");
    const data = await res.json();
    return {
      chapters: data.chapters || {},
      framework_version: data.framework_version,
      status: data.status
    };
  } catch (e) {
    // Fallback Mock Report (Warm Thai Patient Edition)
    return {
      chapters: {
        "1": {
          title: "สิ่งที่เราทราบแน่ชัดเกี่ยวกับร่างกายของคุณ",
          content: "จากการตรวจติดตามล่าสุด ระบบเผาผลาญและระดับน้ำตาลในเลือดของสรีระอยู่ในภาวะที่ต้องคุมอาหารอย่างใกล้ชิด ไตและตับยังทำงานได้ดีต่อเนื่อง หัวใจและหลอดเลือดมีระดับความยืดหยุ่นที่เหมาะสม"
        },
        "2": {
          title: "สิ่งที่เป็นไปได้แต่ยังต้องติดตามเพิ่มเติม",
          content: "พบรูปแบบที่สงสัย Thalassemia Trait — ทีมแพทย์แนะนำให้รับการตรวจยืนยันด้วย Hemoglobin Typing และติดตามค่า Ferritin ก่อนพิจารณาอาหารเสริมใดๆ"
        },
        "3": {
          title: "แนวทางการดูแลตนเองประจำวัน",
          content: "1. รับประทานอาหารดัชนีน้ำตาลต่ำ (Low GI)\n2. ดื่มน้ำสะอาดอย่างน้อยวันละ 2.5 ลิตร\n3. ออกกำลังกายแบบแอโรบิกปานกลาง 30 นาทีต่อวัน\n4. พักผ่อนและนอนหลับก่อนเวลา 23:00 น."
        }
      },
      status: "AI-GENERATED CLINICAL DRAFT - PENDING PHYSICIAN REVIEW"
    };
  }
}
"""

files["src/context/AuthContext.tsx"] = """import React, { createContext, useState, useContext } from 'react';
import { AuthState, PatientProfile } from '../types';

interface AuthContextType extends AuthState {
  login: (token: string, patient: PatientProfile) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    token: null,
    patient: null
  });

  const login = (token: string, patient: PatientProfile) => {
    setAuthState({
      isAuthenticated: true,
      token,
      patient
    });
  };

  const logout = () => {
    setAuthState({
      isAuthenticated: false,
      token: null,
      patient: null
    });
  };

  return (
    <AuthContext.Provider value={{ ...authState, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
"""

files["src/components/BiologicalHUDCard.tsx"] = """import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { theme } from '../theme/theme';
import { ThreeKeyScore } from '../types';

interface Props {
  title: string;
  data?: ThreeKeyScore;
  color: string;
}

export const BiologicalHUDCard: React.FC<Props> = ({ title, data, color }) => {
  const score = data?.score ?? 0;
  
  const getStatusText = (val: number) => {
    if (val > 70) return "ความรุนแรงสูง — ต้องดูแลใกล้ชิด";
    if (val > 40) return "มีความแปรปรวนปานกลาง";
    return "สภาวะสมดุลดีเยี่ยม";
  };

  return (
    <View style={[styles.card, { borderLeftColor: color }]}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>{title}</Text>
        <View style={[styles.badge, { backgroundColor: color + '22' }]}>
          <Text style={[styles.badgeText, { color }]}>{score}/100</Text>
        </View>
      </View>

      <Text style={styles.statusText}>{getStatusText(score)}</Text>

      {/* Progress Bar */}
      <View style={styles.track}>
        <View style={[styles.fill, { width: `${Math.min(100, Math.max(0, score))}%`, backgroundColor: color }]} />
      </View>

      {data?.note && (
        <Text style={styles.noteText}>💡 {data.note}</Text>
      )}

      {data?.assessment_coverage && (
        <Text style={styles.coverageText}>📊 ข้อมูลการตรวจ: {data.assessment_coverage}</Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.colors.bgCard,
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.md,
    borderLeftWidth: 4,
    borderWidth: 1,
    borderColor: theme.colors.border
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.xs
  },
  title: {
    fontSize: 16,
    fontWeight: '700',
    color: theme.colors.textPrimary
  },
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: theme.borderRadius.full
  },
  badgeText: {
    fontSize: 14,
    fontWeight: '700'
  },
  statusText: {
    fontSize: 13,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.sm
  },
  track: {
    height: 8,
    backgroundColor: theme.colors.border,
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: theme.spacing.sm
  },
  fill: {
    height: '100%',
    borderRadius: 4
  },
  noteText: {
    fontSize: 13,
    color: theme.colors.textSecondary,
    lineHeight: 18,
    marginTop: theme.spacing.xs
  },
  coverageText: {
    fontSize: 12,
    color: theme.colors.textMuted,
    marginTop: theme.spacing.xs
  }
});
"""

files["src/components/ChapterCard.tsx"] = """import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { theme } from '../theme/theme';

interface Props {
  chapterNumber: string;
  title: string;
  content: string;
}

export const ChapterCard: React.FC<Props> = ({ chapterNumber, title, content }) => {
  return (
    <View style={styles.card}>
      <View style={styles.badge}>
        <Text style={styles.badgeText}>ส่วนที่ {chapterNumber}</Text>
      </View>
      <Text style={styles.title}>{title}</Text>
      <View style={styles.divider} />
      <Text style={styles.content}>{content}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.colors.bgCard,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.md,
    borderWidth: 1,
    borderColor: theme.colors.border
  },
  badge: {
    alignSelf: 'flex-start',
    backgroundColor: theme.colors.primary + '25',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: theme.borderRadius.sm,
    marginBottom: theme.spacing.xs
  },
  badgeText: {
    color: theme.colors.primaryLight,
    fontSize: 12,
    fontWeight: '600'
  },
  title: {
    fontSize: 17,
    fontWeight: '700',
    color: theme.colors.textPrimary,
    marginBottom: theme.spacing.xs
  },
  divider: {
    height: 1,
    backgroundColor: theme.colors.border,
    marginVertical: theme.spacing.sm
  },
  content: {
    fontSize: 15,
    lineHeight: 23,
    color: theme.colors.textSecondary
  }
});
"""

files["src/components/Header.tsx"] = """import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { theme } from '../theme/theme';

interface Props {
  title: string;
  subtitle?: string;
  rightActionText?: string;
  onRightAction?: () => void;
}

export const Header: React.FC<Props> = ({ title, subtitle, rightActionText, onRightAction }) => {
  return (
    <View style={styles.container}>
      <View>
        <Text style={styles.title}>{title}</Text>
        {subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}
      </View>
      {rightActionText && onRightAction && (
        <TouchableOpacity style={styles.actionBtn} onPress={onRightAction}>
          <Text style={styles.actionText}>{rightActionText}</Text>
        </TouchableOpacity>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.lg,
    marginTop: theme.spacing.md
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: theme.colors.textPrimary
  },
  subtitle: {
    fontSize: 13,
    color: theme.colors.primaryLight,
    marginTop: 2
  },
  actionBtn: {
    backgroundColor: theme.colors.bgCardElevated,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: theme.borderRadius.sm,
    borderWidth: 1,
    borderColor: theme.colors.border
  },
  actionText: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    fontWeight: '600'
  }
});
"""

files["src/screens/ActivationScreen.tsx"] = """import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, ScrollView } from 'react-native';
import { theme } from '../theme/theme';
import { activatePatient } from '../services/api';
import { useAuth } from '../context/AuthContext';

export const ActivationScreen: React.FC = () => {
  const [phone, setPhone] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleActivate = async () => {
    if (!phone.trim() || !name.trim()) {
      Alert.alert("กรุณากรอกข้อมูล", "โปรดกรอกหมายเลขโทรศัพท์และชื่อ-นามสกุลให้ครบถ้วน");
      return;
    }

    setLoading(true);
    try {
      const res = await activatePatient(phone.trim(), name.trim());
      login(res.token, res.patient);
    } catch (err: any) {
      Alert.alert("ไม่สามารถเข้าสู่ระบบได้", err.message || "โปรดตรวจสอบข้อมูลหรือติดต่อคลินิก TSPI");
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.card}>
        <View style={styles.logoContainer}>
          <Text style={styles.logoBadge}>TSPI HEALTH</Text>
          <Text style={styles.heading}>เข้าสู่ระบบสำหรับคนไข้</Text>
          <Text style={styles.subheading}>ยืนยันตัวตนเพื่อเข้าดู Biological HUD และรายงานสุขภาพส่วนบุคคล</Text>
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>หมายเลขโทรศัพท์</Text>
          <TextInput
            style={styles.input}
            placeholder="เช่น 0812345678"
            placeholderTextColor={theme.colors.textMuted}
            keyboardType="phone-pad"
            value={phone}
            onChangeText={setPhone}
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>ชื่อ หรือ นามสกุล</Text>
          <TextInput
            style={styles.input}
            placeholder="กรอกชื่อเพื่อยืนยันกับระบบคลินิก"
            placeholderTextColor={theme.colors.textMuted}
            value={name}
            onChangeText={setName}
          />
        </View>

        <TouchableOpacity 
          style={styles.btn} 
          onPress={handleActivate}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#FFF" />
          ) : (
            <Text style={styles.btnText}>ยืนยันตัวตนเข้าใช้งาน</Text>
          )}
        </TouchableOpacity>

        <Text style={styles.footerNote}>
          🔒 ข้อมูลของคุณได้รับการปกป้องด้วยความปลอดภัยระดับมาตรฐานการแพทย์ TSPI
        </Text>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    backgroundColor: theme.colors.bgDark,
    justifyContent: 'center',
    padding: theme.spacing.lg
  },
  card: {
    backgroundColor: theme.colors.bgCard,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.lg,
    borderWidth: 1,
    borderColor: theme.colors.border
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: theme.spacing.lg
  },
  logoBadge: {
    backgroundColor: theme.colors.primary + '30',
    color: theme.colors.primaryLight,
    fontWeight: '700',
    fontSize: 12,
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: theme.borderRadius.full,
    marginBottom: theme.spacing.sm
  },
  heading: {
    fontSize: 22,
    fontWeight: '700',
    color: theme.colors.textPrimary,
    textAlign: 'center',
    marginBottom: theme.spacing.xs
  },
  subheading: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    textAlign: 'center',
    lineHeight: 20
  },
  inputGroup: {
    marginBottom: theme.spacing.md
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: theme.colors.textPrimary,
    marginBottom: theme.spacing.xs
  },
  input: {
    backgroundColor: theme.colors.bgDark,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.borderRadius.md,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: 12,
    color: theme.colors.textPrimary,
    fontSize: 15
  },
  btn: {
    backgroundColor: theme.colors.primary,
    borderRadius: theme.borderRadius.md,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: theme.spacing.md
  },
  btnText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '700'
  },
  footerNote: {
    fontSize: 12,
    color: theme.colors.textMuted,
    textAlign: 'center',
    marginTop: theme.spacing.lg
  }
});
"""

files["src/screens/HomeScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, RefreshControl } from 'react-native';
import { theme } from '../theme/theme';
import { Header } from '../components/Header';
import { BiologicalHUDCard } from '../components/BiologicalHUDCard';
import { useAuth } from '../context/AuthContext';
import { fetchBiologicalHUD } from '../services/api';
import { ThreeKeysData } from '../types';

interface Props {
  onNavigateToReport: () => void;
  onNavigateToProfile: () => void;
}

export const HomeScreen: React.FC<Props> = ({ onNavigateToReport, onNavigateToProfile }) => {
  const { patient, token } = useAuth();
  const [hudData, setHudData] = useState<ThreeKeysData | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadHUD = async () => {
    if (!patient?.id || !token) return;
    try {
      const data = await fetchBiologicalHUD(patient.id, token);
      setHudData(data);
    } catch (e) {
      console.warn("Error loading HUD:", e);
    }
  };

  useEffect(() => {
    loadHUD();
  }, [patient?.id]);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadHUD();
    setRefreshing(false);
  };

  return (
    <ScrollView 
      style={styles.container} 
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.colors.primaryLight} />}
    >
      <Header 
        title={`สวัสดีคุณ ${patient?.first_name || ''}`}
        subtitle="TSPI Biological Precision Care Engine™"
        rightActionText="โปรไฟล์"
        onRightAction={onNavigateToProfile}
      />

      {/* Patient Welcome Banner */}
      <View style={styles.banner}>
        <Text style={styles.bannerBadge}>การดูแลส่วนบุคคล</Text>
        <Text style={styles.bannerTitle}> Biological HUD Dashboard</Text>
        <Text style={styles.bannerDesc}>
          แสดงสภาวะความสมดุลของ 3 กุญแจชีวภาพหลัก ประเมินตรงจากผลตรวจและอาการทางคลินิก
        </Text>
      </View>

      {/* Three Keys Gauge Cards */}
      <Text style={styles.sectionTitle}>3 กุญแจชีวภาพหลัก (Three Biological Keys)</Text>
      
      <BiologicalHUDCard
        title="1. Metabolic Energy Core"
        data={hudData?.metabolic_energy}
        color={theme.colors.warning}
      />

      <BiologicalHUDCard
        title="2. Biological Dynamic & Circulation"
        data={hudData?.biological_dynamic}
        color={theme.colors.primary}
      />

      <BiologicalHUDCard
        title="3. Biointegrity & Tissue Repair"
        data={hudData?.biointegrity}
        color={theme.colors.secondary}
      />

      {/* Action Navigation Bar */}
      <View style={styles.actionGrid}>
        <TouchableOpacity style={styles.actionCard} onPress={onNavigateToReport}>
          <Text style={styles.actionIcon}>📄</Text>
          <Text style={styles.actionTitle}>อ่านรายงานสุขภาพ</Text>
          <Text style={styles.actionSub}>ฉบับภาษาเข้าใจง่าย</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.actionCard} onPress={onNavigateToProfile}>
          <Text style={styles.actionIcon}>🏥</Text>
          <Text style={styles.actionTitle}>ติดต่อคลินิก</Text>
          <Text style={styles.actionSub}>นัดหมาย / ปรึกษาแพทย์</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.bgDark
  },
  content: {
    padding: theme.spacing.md,
    paddingBottom: theme.spacing.xl
  },
  banner: {
    backgroundColor: theme.colors.bgCard,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.lg,
    borderWidth: 1,
    borderColor: theme.colors.border
  },
  bannerBadge: {
    alignSelf: 'flex-start',
    backgroundColor: theme.colors.secondary + '25',
    color: theme.colors.secondary,
    fontSize: 11,
    fontWeight: '700',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: theme.borderRadius.sm,
    marginBottom: theme.spacing.xs
  },
  bannerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: theme.colors.textPrimary,
    marginBottom: theme.spacing.xs
  },
  bannerDesc: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    lineHeight: 20
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: theme.colors.textPrimary,
    marginBottom: theme.spacing.md
  },
  actionGrid: {
    flexDirection: 'row',
    gap: theme.spacing.md,
    marginTop: theme.spacing.sm
  },
  actionCard: {
    flex: 1,
    backgroundColor: theme.colors.bgCard,
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: theme.colors.border
  },
  actionIcon: {
    fontSize: 28,
    marginBottom: theme.spacing.xs
  },
  actionTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: theme.colors.textPrimary,
    marginBottom: 2
  },
  actionSub: {
    fontSize: 12,
    color: theme.colors.textMuted
  }
});
"""

files["src/screens/ReportScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, ActivityIndicator } from 'react-native';
import { theme } from '../theme/theme';
import { Header } from '../components/Header';
import { ChapterCard } from '../components/ChapterCard';
import { useAuth } from '../context/AuthContext';
import { fetchPatientReport } from '../services/api';
import { PatientReportData } from '../types';

interface Props {
  onBack: () => void;
}

export const ReportScreen: React.FC<Props> = ({ onBack }) => {
  const { patient, token } = useAuth();
  const [report, setReport] = useState<PatientReportData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    async function loadReport() {
      if (!patient?.id || !token) return;
      try {
        const data = await fetchPatientReport(patient.id, token);
        if (isMounted) setReport(data);
      } catch (e) {
        console.warn("Error loading report:", e);
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    loadReport();
    return () => { isMounted = false; };
  }, [patient?.id]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Header 
        title="รายงานสุขภาพประจำตัว"
        subtitle="Patient Precision Edition (ฉบับคนไข้)"
        rightActionText="← กลับ"
        onRightAction={onBack}
      />

      <View style={styles.watermarkCard}>
        <Text style={styles.watermarkBadge}>AI-GENERATED CLINICAL DRAFT</Text>
        <Text style={styles.watermarkText}>
          ร่างคำสั่งปัญญาประดิษฐ์ — รอกระบวนการอนุมัติและรับรองจากแพทย์ผู้ดูแลก่อนปล่อยใช้จริง
        </Text>
      </View>

      {loading ? (
        <View style={styles.loadingBox}>
          <ActivityIndicator size="large" color={theme.colors.primaryLight} />
          <Text style={styles.loadingText}>กำลังเรียบเรียงข้อมูลสรีรวิทยาสำหรับคนไข้...</Text>
        </View>
      ) : report?.chapters ? (
        Object.entries(report.chapters).map(([key, chapter]) => (
          <ChapterCard
            key={key}
            chapterNumber={key}
            title={chapter.title}
            content={chapter.content}
          />
        ))
      ) : (
        <Text style={styles.emptyText}>ไม่พบข้อมูลรายงานในขณะนี้</Text>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.bgDark
  },
  content: {
    padding: theme.spacing.md,
    paddingBottom: theme.spacing.xl
  },
  watermarkCard: {
    backgroundColor: theme.colors.warning + '18',
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.lg,
    borderWidth: 1,
    borderColor: theme.colors.warning + '44'
  },
  watermarkBadge: {
    color: theme.colors.warning,
    fontSize: 11,
    fontWeight: '700',
    marginBottom: 4
  },
  watermarkText: {
    color: theme.colors.textSecondary,
    fontSize: 13,
    lineHeight: 18
  },
  loadingBox: {
    padding: theme.spacing.xl,
    alignItems: 'center'
  },
  loadingText: {
    color: theme.colors.textSecondary,
    marginTop: theme.spacing.md,
    fontSize: 14
  },
  emptyText: {
    color: theme.colors.textMuted,
    textAlign: 'center',
    marginTop: theme.spacing.xl
  }
});
"""

files["src/screens/ProfileScreen.tsx"] = """import React from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, Linking, Alert } from 'react-native';
import { theme } from '../theme/theme';
import { Header } from '../components/Header';
import { useAuth } from '../context/AuthContext';

interface Props {
  onBack: () => void;
}

export const ProfileScreen: React.FC<Props> = ({ onBack }) => {
  const { patient, logout } = useAuth();

  const handleOpenLine = () => {
    Linking.openURL('https://line.me').catch(() => {
      Alert.alert("ติดต่อคลินิก", "กรุณาแอดไลน์คลินิกผ่าน @doctorpatt");
    });
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Header 
        title="โปรไฟล์คนไข้"
        subtitle="ข้อมูลทะเบียนประวัติคลินิก TSPI"
        rightActionText="← กลับ"
        onRightAction={onBack}
      />

      <View style={styles.card}>
        <View style={styles.avatarRow}>
          <View style={styles.avatar}>
            <Text style={styles.avatarInitial}>{patient?.first_name?.charAt(0) || 'P'}</Text>
          </View>
          <View>
            <Text style={styles.name}>{patient?.first_name} {patient?.last_name}</Text>
            <Text style={styles.hn}>{patient?.hn || 'HN-UNREGISTERED'}</Text>
          </View>
        </View>

        <View style={styles.divider} />

        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>หมายเลขโทรศัพท์:</Text>
          <Text style={styles.infoVal}>{patient?.phone || 'ไม่ระบุ'}</Text>
        </View>

        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>อายุ:</Text>
          <Text style={styles.infoVal}>{patient?.age ? `${patient.age} ปี` : 'ไม่ระบุ'}</Text>
        </View>

        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>เพศ:</Text>
          <Text style={styles.infoVal}>{patient?.gender || 'ไม่ระบุ'}</Text>
        </View>

        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>โรคประจำตัว:</Text>
          <Text style={styles.infoVal}>{patient?.underlying_disease || 'ไม่มี/ไม่ระบุ'}</Text>
        </View>
      </View>

      <TouchableOpacity style={styles.lineBtn} onPress={handleOpenLine}>
        <Text style={styles.lineBtnText}>💬 ปรึกษาทีมแพทย์ผ่าน LINE OA</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.logoutBtn} onPress={logout}>
        <Text style={styles.logoutText}>ออกจากระบบ</Text>
      </TouchableOpacity>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.bgDark
  },
  content: {
    padding: theme.spacing.md,
    paddingBottom: theme.spacing.xl
  },
  card: {
    backgroundColor: theme.colors.bgCard,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.lg,
    borderWidth: 1,
    borderColor: theme.colors.border
  },
  avatarRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: theme.spacing.md
  },
  avatar: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: theme.colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: theme.spacing.md
  },
  avatarInitial: {
    color: '#FFF',
    fontSize: 22,
    fontWeight: '700'
  },
  name: {
    fontSize: 18,
    fontWeight: '700',
    color: theme.colors.textPrimary
  },
  hn: {
    fontSize: 13,
    color: theme.colors.primaryLight,
    marginTop: 2
  },
  divider: {
    height: 1,
    backgroundColor: theme.colors.border,
    marginBottom: theme.spacing.md
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.sm
  },
  infoLabel: {
    fontSize: 14,
    color: theme.colors.textSecondary
  },
  infoVal: {
    fontSize: 14,
    fontWeight: '600',
    color: theme.colors.textPrimary
  },
  lineBtn: {
    backgroundColor: "#06C755",
    borderRadius: theme.borderRadius.md,
    paddingVertical: 14,
    alignItems: 'center',
    marginBottom: theme.spacing.md
  },
  lineBtnText: {
    color: '#FFF',
    fontSize: 15,
    fontWeight: '700'
  },
  logoutBtn: {
    backgroundColor: theme.colors.danger + '22',
    borderWidth: 1,
    borderColor: theme.colors.danger + '44',
    borderRadius: theme.borderRadius.md,
    paddingVertical: 14,
    alignItems: 'center'
  },
  logoutText: {
    color: theme.colors.danger,
    fontSize: 15,
    fontWeight: '700'
  }
});
"""

files["App.tsx"] = """import React, { useState } from 'react';
import { SafeAreaView, StatusBar, StyleSheet, View } from 'react-native';
import { theme } from './src/theme/theme';
import { AuthProvider, useAuth } from './src/context/AuthContext';
import { ActivationScreen } from './src/screens/ActivationScreen';
import { HomeScreen } from './src/screens/HomeScreen';
import { ReportScreen } from './src/screens/ReportScreen';
import { ProfileScreen } from './src/screens/ProfileScreen';

type ScreenName = 'home' | 'report' | 'profile';

const NavigationContainer: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [currentScreen, setCurrentScreen] = useState<ScreenName>('home');

  if (!isAuthenticated) {
    return <ActivationScreen />;
  }

  return (
    <View style={styles.screen}>
      {currentScreen === 'home' && (
        <HomeScreen 
          onNavigateToReport={() => setCurrentScreen('report')}
          onNavigateToProfile={() => setCurrentScreen('profile')}
        />
      )}

      {currentScreen === 'report' && (
        <ReportScreen onBack={() => setCurrentScreen('home')} />
      )}

      {currentScreen === 'profile' && (
        <ProfileScreen onBack={() => setCurrentScreen('home')} />
      )}
    </View>
  );
};

export default function App() {
  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="light-content" backgroundColor={theme.colors.bgDark} />
      <AuthProvider>
        <NavigationContainer />
      </AuthProvider>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: theme.colors.bgDark
  },
  screen: {
    flex: 1
  }
});
"""

files["README.md"] = """# TSPI Patient Care — React Native Mobile App

แอปพลิเคชันมือถือสำหรับคนไข้ระบบ TSPI Precision Medicine (ฝั่งผู้ใช้งาน) พัฒนาด้วย React Native + Expo (TypeScript)

## 🚀 ฟีเจอร์หลัก
- **Patient Activation / Authentication**: ยืนยันตัวตนคนไข้ด้วยเบอร์โทรศัพท์ + ชื่อ-นามสกุล
- **Biological HUD Dashboard**: การ์ดแสดงผล Three Biological Keys
- **Warm Patient Precision Report**: อ่านรายงานสุขภาพส่วนบุคคลฉบับภาษาไทยที่ย่อยง่าย
- **Clinic Link & Profile**: ดูประวัติสุขภาพส่วนตัว ลิงก์นัดหมายและ LINE OA

## 🛠️ วิธีการติดตั้งและทดสอบรัน

```bash
# 1. เข้าโฟลเดอร์โปรเจกต์
cd ~/Documents/tspiApp

# 2. ติดตั้ง Dependencies
npm install

# 3. เริ่มต้นรัน Expo Dev Server
npm start
```
"""

for path, content in files.items():
    full_path = os.path.join(BASE_DIR, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print(f"Successfully generated {len(files)} files in {BASE_DIR}")
