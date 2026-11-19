import { useEffect, useMemo, useState,  useRef ,type FormEvent } from "react";
import "./App.css";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { jsPDF } from "jspdf";
import * as XLSX from "xlsx";

const API_BASE_URL = "http://127.0.0.1:8000";

const roles = [
 "Admin",
  "User",
];

interface User {
  id: number;
  full_name: string;
  email: string;
  role: string;
  is_active?: number;
  created_at?: string;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

interface Asset {
  id: number;
  asset_code: string;
  name: string;
  asset_type: string;
  location: string;
  latitude?: number | null;
  longitude?: number | null;
  construction_year: number | null;
  material: string;
  department: string;
  inspection_frequency: string;
  created_by: number;
  created_at: string;
  updated_at: string;
}

interface AssetForm {
  asset_code: string;
  name: string;
  asset_type: string;
  location: string;
  latitude: string;
  longitude: string;
  construction_year: string;
  material: string;
  department: string;
  inspection_frequency: string;
}

interface Inspection {
  id: number;
  inspection_code: string;
  asset_id: number;
  inspection_date: string;
  inspection_type: string;
  assigned_inspector_id: number | null;
  status: "Scheduled" | "In Progress" | "Completed" | "Cancelled";
  notes: string | null;
  asset_code: string;
  asset_name: string;
  asset_type: string;
  asset_location: string;
  inspector_name: string | null;
}

interface Inspector {
  id: number;
  full_name: string;
  email: string;
  role: string;
}

interface InspectionForm {
  inspection_code: string;
  asset_id: string;
  inspection_date: string;
  inspection_type: string;
  assigned_inspector_id: string;
  status: Inspection["status"];
  notes: string;
}

const emptyInspectionForm: InspectionForm = {
  inspection_code: "",
  asset_id: "",
  inspection_date: new Date().toISOString().slice(0, 10),
  inspection_type: "Routine Visual Inspection",
  assigned_inspector_id: "",
  status: "Scheduled",
  notes: "",
};

const emptyAssetForm: AssetForm = {
  asset_code: "",
  name: "",
  asset_type: "Bridge",
  location: "",
  latitude: "",
  longitude: "",
  construction_year: "",
  material: "",
  department: "",
  inspection_frequency: "Every 6 Months",
};

const navigation = [
  { name: "Overview", icon: "▦" },
  { name: "Assets", icon: "▤" },
  { name: "Inspections", icon: "⌕" },
  { name: "AI Damage Analysis", icon: "◈" },
  { name: "Damage Reports", icon: "▧" },
  { name: "Damage Analytics", icon: "▥" },
  { name: "Historical Comparison", icon: "↔" },
  { name: "Infrastructure Map", icon: "⌖" },
  { name: "Maintenance", icon: "⚒" },
  { name: "User Management", icon: "♙", adminOnly: true },
];

const inspections = [
  {
    id: "INS-2026-001",
    asset: "Central Office Building",
    type: "Building",
    date: "14 Nov 2026",
    inspector: "Inspection Team",
    status: "Completed",
    severity: "Moderate",
  },
  {
    id: "INS-2026-002",
    asset: "North Road Section",
    type: "Road",
    date: "13 Nov 2026",
    inspector: "Inspection Team",
    status: "In Progress",
    severity: "Low",
  },
  {
    id: "INS-2026-003",
    asset: "River Bridge",
    type: "Bridge",
    date: "12 Nov 2026",
    inspector: "Inspection Team",
    status: "Pending",
    severity: "High",
  },
];

const damageCategories = [
  { name: "Cracks", count: 42, percent: 70 },
  { name: "Spalling", count: 18, percent: 40 },
  { name: "Corrosion", count: 12, percent: 28 },
  { name: "Surface damage", count: 9, percent: 20 },
];

function App() {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const [role, setRole] = useState("Admin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [user, setUser] = useState<User | null>(null);
  const [managedUsers, setManagedUsers] = useState<User[]>([]);
  // Restore login session after page refresh
useEffect(() => {
  const savedToken = sessionStorage.getItem("access_token");
  const savedUser = sessionStorage.getItem("user");

  if (savedToken && savedUser) {
    try {
      setUser(JSON.parse(savedUser) as User);
    } catch {
      sessionStorage.removeItem("access_token");
      sessionStorage.removeItem("user");
    }
  }
}, []);
  const [usersLoading, setUsersLoading] = useState(false);
  const [usersError, setUsersError] = useState("");
  const [usersSuccess, setUsersSuccess] = useState("");
  const [userSearch, setUserSearch] = useState("");
  const [activePage, setActivePage] = useState("Overview");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [readNotificationIds, setReadNotificationIds] = useState<number[]>([]);

  // Asset management state
  const [assets, setAssets] = useState<Asset[]>([]);
  const [assetsLoading, setAssetsLoading] = useState(false);
  const [assetError, setAssetError] = useState("");
  const [assetSuccess, setAssetSuccess] = useState("");
  const [assetSearch, setAssetSearch] = useState("");
  const [showAssetForm, setShowAssetForm] = useState(false);
  const [editingAsset, setEditingAsset] = useState<Asset | null>(null);
  const [assetForm, setAssetForm] = useState<AssetForm>(emptyAssetForm);
  const [assetSaving, setAssetSaving] = useState(false);
  // Infrastructure map setup
useEffect(() => {
  if (activePage !== "Infrastructure Map" || !mapContainerRef.current) {
    return;
  }

  const map = L.map(mapContainerRef.current).setView(
    [12.2958, 76.6394],
    11
  );

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);

  const markers: L.Marker[] = [];

  assets.forEach((asset) => {
    if (asset.latitude == null || asset.longitude == null) {
      return;
    }

    const popup = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = asset.name;

    const details = document.createElement("p");
    details.textContent = `${asset.asset_code} - ${asset.location}`;

    popup.appendChild(title);
    popup.appendChild(details);

    const marker = L.marker([
      asset.latitude,
      asset.longitude,
    ])
      .addTo(map)
      .bindPopup(popup);

    markers.push(marker);
  });

  if (markers.length > 0) {
    map.fitBounds(
      L.featureGroup(markers).getBounds().pad(0.15)
    );
  }

  return () => {
    map.remove();
  };
}, [activePage, assets]);

  // Inspection management state
  const [inspectionRecords, setInspectionRecords] = useState<Inspection[]>([]);
  const [inspectors, setInspectors] = useState<Inspector[]>([]);
  const [inspectionsLoading, setInspectionsLoading] = useState(false);
  const [inspectionError, setInspectionError] = useState("");
  const [inspectionSuccess, setInspectionSuccess] = useState("");
  const [inspectionSearch, setInspectionSearch] = useState("");
  const [inspectionStatusFilter, setInspectionStatusFilter] = useState("");
  const [showInspectionForm, setShowInspectionForm] = useState(false);
  const [editingInspection, setEditingInspection] = useState<Inspection | null>(null);
  const [inspectionForm, setInspectionForm] = useState<InspectionForm>(emptyInspectionForm);
  const [inspectionSaving, setInspectionSaving] = useState(false);
  // AI Damage Analysis state
const [selectedImage, setSelectedImage] = useState<File | null>(null);
const [multipleAnalysisResults, setMultipleAnalysisResults] = useState<
  Array<{
    filename: string;
    crack_percentage: number;
    severity: string;
    severity_description: string;
    crack_length_pixels: number;
    average_crack_width_pixels: number;
    assessment_note: string;
    mask: string;
    overlay: string;
    confidence_heatmap: string;
    message: string;
    originalImage: string;
  }>
>([]);
const totalImagesAnalyzed = multipleAnalysisResults.length;

const maintenancePriorities = multipleAnalysisResults.map((result) => ({
  ...result,
  priority:
    result.severity.toLowerCase() === "severe"
      ? "High"
      : result.severity.toLowerCase() === "moderate"
      ? "Medium"
      : "Low",
  recommendation:
    result.severity.toLowerCase() === "severe"
      ? "Immediate engineering inspection recommended."
      : result.severity.toLowerCase() === "moderate"
      ? "Schedule maintenance and monitor damage."
      : "Continue routine monitoring.",
}));

const averageCrackPercentage =
  totalImagesAnalyzed > 0
    ? multipleAnalysisResults.reduce(
        (sum, result) => sum + result.crack_percentage,
        0
      ) / totalImagesAnalyzed
    : 0;

const highestCrackPercentage =
  totalImagesAnalyzed > 0
    ? Math.max(
        ...multipleAnalysisResults.map(
          (result) => result.crack_percentage
        )
      )
    : 0;

const lowestCrackPercentage =
  totalImagesAnalyzed > 0
    ? Math.min(
        ...multipleAnalysisResults.map(
          (result) => result.crack_percentage
        )
      )
    : 0;
const [imagePreview, setImagePreview] = useState("");
const [selectedImages, setSelectedImages] = useState<File[]>([]);
const selectedImagePreviews = useMemo(
  () => selectedImages.map((image) => URL.createObjectURL(image)),
  [selectedImages]
);

useEffect(() => {
  return () => {
    selectedImagePreviews.forEach((url) => URL.revokeObjectURL(url));
  };
}, [selectedImagePreviews]);
const [analysisLoading, setAnalysisLoading] = useState(false);
const [analysisHistory, setAnalysisHistory] = useState<
  Array<{
    id: number;
    filename: string;
    crack_percentage: number;
    analyzed_by: number;
    analyzed_at: string;
  }>
>([]);
const [reportSearch, setReportSearch] = useState("");
const [appliedReportSearch, setAppliedReportSearch] = useState("");
const savedMaintenanceRecords = [...analysisHistory].sort(
  (a, b) => b.crack_percentage - a.crack_percentage
);
const notifications = analysisHistory
  .filter((record) => record.crack_percentage >= 5)
  .map((record) => ({
    id: record.id,
    title: "High Priority Damage Detected",
    message: `${record.filename} has ${record.crack_percentage.toFixed(2)}% crack pixels.`,
    date: record.analyzed_at,
  }));

const unreadNotificationCount = notifications.filter(
  (notification) => !readNotificationIds.includes(notification.id)
).length;

const [historyLoading, setHistoryLoading] = useState(false);
const [historyError, setHistoryError] = useState("");
const [analysisError, setAnalysisError] = useState("");
const [analysisResult, setAnalysisResult] = useState<{
  filename: string;
  crack_percentage: number;
  mask: string;
  message: string;
} | null>(null);

  const canManageAssets = user?.role === "Admin";
const canDeleteAssets = user?.role === "Admin";

const canManageInspections = user?.role === "Admin";
const canDeleteInspections = user?.role === "Admin";
  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    if (!email.trim() || !password) {
      setError("Please enter your email and password.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Login failed. Please try again.");
      }

      const loginData = data as LoginResponse;

      if (!loginData.user || !loginData.access_token) {
        throw new Error("Invalid response received from the server.");
      }

      if (loginData.user.role !== role) {
        throw new Error(
          "Selected role does not match your registered account."
        );
      }

      sessionStorage.setItem("access_token", loginData.access_token);
      sessionStorage.setItem("user", JSON.stringify(loginData.user));

      setUser(loginData.user);
      setPassword("");
      setActivePage("Overview");
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "Unable to connect to the backend. Check whether the server is running."
          : err instanceof Error
            ? err.message
            : "Something went wrong. Please try again."
      );
    } finally {
      setLoading(false);
    }
      };
// Handle multiple image selection
const handleImageSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
  const files = Array.from(event.target.files ?? []);

  if (files.length === 0) return;

  const invalidFile = files.find(
    (file) => !file.type.startsWith("image/")
  );

  if (invalidFile) {
    setAnalysisError("Please select only valid image files.");
    event.target.value = "";
    return;
  }

  setSelectedImages((previousImages) => {
    const combinedImages = [...previousImages, ...files];

    return combinedImages.filter(
      (file, index, array) =>
        array.findIndex(
          (item) => item.name === file.name && item.size === file.size
        ) === index
    );
  });

  setSelectedImage(files[0]);
  setImagePreview(URL.createObjectURL(files[0]));
  setAnalysisResult(null);
  setMultipleAnalysisResults([]);
  setAnalysisError("");

  event.target.value = "";
};
// Remove an individual selected image
const handleRemoveSelectedImage = (indexToRemove: number) => {
  const updatedImages = selectedImages.filter(
    (_, index) => index !== indexToRemove
  );

  setSelectedImages(updatedImages);

  setSelectedImage(updatedImages[0] ?? null);

  setImagePreview(
    updatedImages.length > 0
      ? URL.createObjectURL(updatedImages[0])
      : ""
  );

  setMultipleAnalysisResults([]);
  setAnalysisResult(null);
  setAnalysisError("");
};
// Analyze multiple uploaded images using the existing U-Net API
const handleAnalyzeImage = async () => {
  if (selectedImages.length === 0) {
    setAnalysisError("Please upload at least one image first.");
    return;
  }

  setAnalysisLoading(true);
  setAnalysisError("");
  setAnalysisResult(null);
  setMultipleAnalysisResults([]);

  const results: Array<{
    filename: string;
    crack_percentage: number;
    severity: string;
    severity_description: string;
    assessment_note: string;
    mask: string;
    overlay: string;
    confidence_heatmap: string;
    crack_length_pixels: number;
    average_crack_width_pixels: number;
    message: string;
    originalImage: string;
  }> = [];

  try {
    for (const image of selectedImages) {
      const formData = new FormData();
      formData.append("file", image);

      
const token = sessionStorage.getItem("access_token");

if (!token) {
  throw new Error("Please sign in again to analyze images.");
}

const response = await fetch(`${API_BASE_URL}/predict`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${token}`,
  },
  body: formData,
});

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          `${image.name}: ${data.detail || "Image analysis failed."}`
        );
      }

      results.push({
  ...data,
  originalImage: URL.createObjectURL(image),
});
      setMultipleAnalysisResults([...results]);
    }
  } catch (err) {
    setAnalysisError(
      err instanceof Error
        ? err.message
        : "Unable to analyze the images."
    );
  } finally {
    setAnalysisLoading(false);
  }
};
const handleClearAnalysis = () => {
  setSelectedImage(null);
  setSelectedImages([]);
  setImagePreview("");
  setAnalysisResult(null);
  setMultipleAnalysisResults([]);
  setAnalysisError("");
};

const handleDownloadDamageReport = () => {
  if (analysisHistory.length === 0) {
    alert("No saved analysis records available to download.");
    return;
  }

  const doc = new jsPDF();

  const generatedDate = new Date().toLocaleString();

  const percentages = analysisHistory.map(
    (record) => record.crack_percentage
  );

  const totalImages = analysisHistory.length;

  const average =
    percentages.reduce((sum, value) => sum + value, 0) /
    totalImages;

  const highest = Math.max(...percentages);
  const lowest = Math.min(...percentages);

  // Report heading
  doc.setFontSize(18);
  doc.text("InfraScan - AI Damage Assessment Report", 14, 20);

  doc.setFontSize(10);
  doc.text(`Generated on: ${generatedDate}`, 14, 30);

  // Summary
  doc.setFontSize(14);
  doc.text("Analysis Summary", 14, 45);

  doc.setFontSize(11);
  doc.text(`Total Images Analyzed: ${totalImages}`, 14, 57);
  doc.text(`Average Crack Percentage: ${average.toFixed(2)}%`, 14, 66);
  doc.text(`Highest Crack Percentage: ${highest.toFixed(2)}%`, 14, 75);
  doc.text(`Lowest Crack Percentage: ${lowest.toFixed(2)}%`, 14, 84);

  // Individual image records
  doc.setFontSize(14);
  doc.text("Saved Image Analysis Records", 14, 102);

  doc.setFontSize(10);

  let y = 114;

  analysisHistory.forEach((record, index) => {
    if (y > 265) {
      doc.addPage();
      y = 20;
    }

    doc.text(`${index + 1}. ${record.filename}`, 14, y);

    doc.text(
      `Crack Pixel Percentage: ${record.crack_percentage.toFixed(2)}%`,
      20,
      y + 8
    );

    doc.text(
      `Analysis Date: ${record.analyzed_at}`,
      20,
      y + 16
    );

    y += 25;
  });

  // Disclaimer
  if (y > 260) {
    doc.addPage();
    y = 20;
  }

  doc.setFontSize(9);

  doc.text(
    "Note: Crack percentage is an AI-based image estimate and is not a structural safety assessment.",
    14,
    y + 5,
    { maxWidth: 180 }
  );

  doc.save("InfraScan_Damage_Assessment_Report.pdf");
};

const handleDownloadCSVReport = () => {
  if (filteredAnalysisHistory.length === 0) {
    alert("No analysis records available to export.");
    return;
  }

  const headers = [
    "Sl. No.",
    "Image Name",
    "Crack Pixel Percentage",
    "Analysis Date",
    "Analysis Status",
  ];

  const escapeCSV = (value: string | number) =>
    `"${String(value).replace(/"/g, '""')}"`;

  const rows = filteredAnalysisHistory.map((record, index) => [
    index + 1,
    record.filename,
    `${record.crack_percentage.toFixed(2)}%`,
    record.analyzed_at,
    "Completed",
  ]);

  const csvContent = [
    headers.map(escapeCSV).join(","),
    ...rows.map((row) => row.map(escapeCSV).join(",")),
  ].join("\n");

  const blob = new Blob(["\uFEFF" + csvContent], {
    type: "text/csv;charset=utf-8;",
  });

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = "InfraScan_Damage_Analysis_Report.csv";
  link.click();

  URL.revokeObjectURL(url);
};

const handleDownloadExcelReport = () => {
  if (filteredAnalysisHistory.length === 0) {
    alert("No analysis records available to export.");
    return;
  }

  const rows = [
    [
      "Sl. No.",
      "Image Name",
      "Crack Pixel Percentage",
      "Analysis Date",
      "Analysis Status",
    ],
    ...filteredAnalysisHistory.map((record, index) => [
      index + 1,
      record.filename,
      `${record.crack_percentage.toFixed(2)}%`,
      record.analyzed_at,
      "Completed",
    ]),
  ];

  const worksheet = XLSX.utils.aoa_to_sheet(rows);

  worksheet["!cols"] = [
    { wch: 10 },
    { wch: 25 },
    { wch: 28 },
    { wch: 22 },
    { wch: 18 },
  ];

  const workbook = XLSX.utils.book_new();

  XLSX.utils.book_append_sheet(
    workbook,
    worksheet,
    "Damage Analysis"
  );

  XLSX.writeFile(
    workbook,
    "InfraScan_Damage_Analysis_Report.xlsx"
  );
};


  const handleLogout = () => {
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("user");
    setUser(null);
    setEmail("");
    setPassword("");
    setError("");
    setAssets([]);
    setInspectionRecords([]);
    setInspectors([]);
    setActivePage("Overview");
  };

  // Load assets from the backend
  const fetchAssets = async (searchValue = "") => {
    const token = sessionStorage.getItem("access_token");

    if (!token) {
      setAssetError("Your session has expired. Please sign in again.");
      return;
    }

    setAssetsLoading(true);
    setAssetError("");

    try {
      const query = searchValue.trim()
        ? `?search=${encodeURIComponent(searchValue.trim())}`
        : "";

      const response = await fetch(
        `${API_BASE_URL}/assets/${query}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to load assets.");
      }

      setAssets(data.assets || []);
    } catch (err) {
      setAssetError(
        err instanceof Error
          ? err.message
          : "Unable to load assets."
      );
    } finally {
      setAssetsLoading(false);
    }
  };

// Load saved AI analysis history from the backend
const fetchAnalysisHistory = async () => {
  const token = sessionStorage.getItem("access_token");

  if (!token) {
    setHistoryError("Please sign in again.");
    return;
  }

  setHistoryLoading(true);
  setHistoryError("");

  try {
    const response = await fetch(
      `${API_BASE_URL}/analysis-history`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.detail || "Unable to load analysis history."
      );
    }

    setAnalysisHistory(data.records || []);
  } catch (err) {
    setHistoryError(
      err instanceof Error
        ? err.message
        : "Unable to load analysis history."
    );
  } finally {
    setHistoryLoading(false);
  }
};
// Load all users for Admin User Management
const fetchManagedUsers = async () => {
  const token = sessionStorage.getItem("access_token");

  if (!token) {
    setUsersError("Please sign in again.");
    return;
  }

  setUsersLoading(true);
  setUsersError("");

  try {
    const response = await fetch(
      `${API_BASE_URL}/auth/users`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.detail || "Unable to load users."
      );
    }

    setManagedUsers(data.users || []);
  } catch (err) {
    setUsersError(
      err instanceof Error
        ? err.message
        : "Unable to load users."
    );
  } finally {
    setUsersLoading(false);
  }
};

// Activate or deactivate a user
const handleUserStatusChange = async (
  managedUser: User
) => {
  const newStatus = managedUser.is_active !== 1;

  const action = newStatus ? "activate" : "deactivate";

  const confirmed = window.confirm(
    `Are you sure you want to ${action} ${managedUser.full_name}?`
  );

  if (!confirmed) return;

  const token = sessionStorage.getItem("access_token");

  if (!token) {
    setUsersError("Please sign in again.");
    return;
  }

  setUsersError("");
  setUsersSuccess("");

  try {
    const response = await fetch(
      `${API_BASE_URL}/auth/users/${managedUser.id}/status?is_active=${newStatus}`,
      {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.detail || "Unable to update user status."
      );
    }

    setUsersSuccess(data.message);
    await fetchManagedUsers();
  } catch (err) {
    setUsersError(
      err instanceof Error
        ? err.message
        : "Unable to update user status."
    );
  }
};

useEffect(() => {
  if (activePage === "User Management" && user?.role === "Admin") {
    fetchManagedUsers();
  }
}, [activePage, user]);

const handleDeleteAnalysis = async (recordId: number) => {
  const confirmed = window.confirm(
    "Are you sure you want to delete this analysis report?"
  );

  if (!confirmed) return;

  try {
    const token = sessionStorage.getItem("access_token");

    const response = await fetch(
      `${API_BASE_URL}/analysis-history/${recordId}`,
      {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Failed to delete report.");
    }

    alert("Analysis report deleted successfully!");

    await fetchAnalysisHistory();
  } catch (error) {
    console.error("Delete error:", error);
    alert(
      error instanceof Error
        ? error.message
        : "Something went wrong while deleting."
    );
  }
};
const filteredAnalysisHistory = analysisHistory.filter((record) =>
  record.filename
    .toLowerCase()
    .includes(appliedReportSearch.trim().toLowerCase())
);



  // Load inspections from the backend.
  const fetchInspections = async (
    searchValue = inspectionSearch,
    statusValue = inspectionStatusFilter
  ) => {
    const token = sessionStorage.getItem("access_token");

    if (!token) {
      setInspectionError("Your session has expired. Please sign in again.");
      return;
    }

    setInspectionsLoading(true);
    setInspectionError("");

    try {
      const params = new URLSearchParams();

      if (searchValue.trim()) {
        params.set("search", searchValue.trim());
      }

      if (statusValue) {
        params.set("status", statusValue);
      }

      const suffix = params.toString() ? `?${params.toString()}` : "";

      const response = await fetch(
        `${API_BASE_URL}/inspections/${suffix}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to load inspections.");
      }

      setInspectionRecords(data.inspections || []);
    } catch (err) {
      setInspectionError(
        err instanceof Error
          ? err.message
          : "Unable to load inspections."
      );
    } finally {
      setInspectionsLoading(false);
    }
  };

  const fetchInspectors = async () => {
    const token = sessionStorage.getItem("access_token");

    if (!token) return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/inspections/inspectors`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to load inspectors.");
      }

      setInspectors(data.inspectors || []);
    } catch (err) {
      setInspectionError(
        err instanceof Error
          ? err.message
          : "Unable to load inspectors."
      );
    }
  };

  useEffect(() => {
    if (user && activePage === "Assets") {
      fetchAssets();
    }
    if (user && activePage === "Infrastructure Map") {
  fetchAssets();
}
if (user && activePage === "Overview") {
  fetchAssets();
  fetchInspections("", "");
  fetchAnalysisHistory();
}

    if (user && activePage === "Inspections") {
      fetchAssets();
      fetchInspections("", "");
      fetchInspectors();
    }
    if (
  user &&
  (
    activePage === "Damage Reports" ||
    activePage === "Damage Analytics" ||
    activePage === "Historical Comparison" ||
    activePage === "Maintenance"
  )
) {
  fetchAnalysisHistory();
}
  }, [user, activePage]);

  const openAddInspectionForm = () => {
    setEditingInspection(null);

    setInspectionForm({
      ...emptyInspectionForm,
      asset_id: assets[0] ? String(assets[0].id) : "",
    });

    setInspectionError("");
    setInspectionSuccess("");
    setShowInspectionForm(true);
  };

  const openEditInspectionForm = (inspection: Inspection) => {
    setEditingInspection(inspection);

    setInspectionForm({
      inspection_code: inspection.inspection_code,
      asset_id: String(inspection.asset_id),
      inspection_date: inspection.inspection_date,
      inspection_type: inspection.inspection_type,
      assigned_inspector_id: inspection.assigned_inspector_id
        ? String(inspection.assigned_inspector_id)
        : "",
      status: inspection.status,
      notes: inspection.notes || "",
    });

    setInspectionError("");
    setInspectionSuccess("");
    setShowInspectionForm(true);
  };

  const handleInspectionFormChange = (
    field: keyof InspectionForm,
    value: string
  ) => {
    setInspectionForm((previous) => ({
      ...previous,
      [field]: value,
    }));
  };

  const handleInspectionSubmit = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    const token = sessionStorage.getItem("access_token");

    if (!token) {
      setInspectionError("Please sign in again.");
      return;
    }

    if (!inspectionForm.asset_id) {
      setInspectionError("Please select an infrastructure asset.");
      return;
    }

    setInspectionSaving(true);
    setInspectionError("");
    setInspectionSuccess("");

    const payload = {
      inspection_code: inspectionForm.inspection_code.trim(),
      asset_id: Number(inspectionForm.asset_id),
      inspection_date: inspectionForm.inspection_date,
      inspection_type: inspectionForm.inspection_type.trim(),
      assigned_inspector_id: inspectionForm.assigned_inspector_id
        ? Number(inspectionForm.assigned_inspector_id)
        : null,
      status: inspectionForm.status,
      notes: inspectionForm.notes.trim() || null,
    };

    try {
      const isEditing = Boolean(editingInspection);

      const response = await fetch(
        isEditing
          ? `${API_BASE_URL}/inspections/${editingInspection!.id}`
          : `${API_BASE_URL}/inspections/`,
        {
          method: isEditing ? "PUT" : "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to save inspection.");
      }

      setShowInspectionForm(false);
      setEditingInspection(null);
      setInspectionForm(emptyInspectionForm);

      setInspectionSuccess(
        isEditing
          ? "Inspection updated successfully."
          : "Inspection created successfully."
      );

      await fetchInspections();
    } catch (err) {
      setInspectionError(
        err instanceof Error
          ? err.message
          : "Unable to save inspection."
      );
    } finally {
      setInspectionSaving(false);
    }
  };

  const handleDeleteInspection = async (inspection: Inspection) => {
    if (!canDeleteInspections) return;

    const confirmed = window.confirm(
      `Are you sure you want to delete ${inspection.inspection_code}?`
    );

    if (!confirmed) return;

    const token = sessionStorage.getItem("access_token");

    if (!token) {
      setInspectionError("Please sign in again.");
      return;
    }

    setInspectionError("");
    setInspectionSuccess("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/inspections/${inspection.id}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to delete inspection.");
      }

      setInspectionSuccess("Inspection deleted successfully.");
      await fetchInspections();
    } catch (err) {
      setInspectionError(
        err instanceof Error
          ? err.message
          : "Unable to delete inspection."
      );
    }
  };

  const handleInspectionSearch = (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();
    fetchInspections(inspectionSearch, inspectionStatusFilter);
  };

  const handleSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    fetchAssets(assetSearch);
  };

  const openAddAssetForm = () => {
    setEditingAsset(null);
    setAssetForm(emptyAssetForm);
    setAssetError("");
    setAssetSuccess("");
    setShowAssetForm(true);
  };

  const openEditAssetForm = (asset: Asset) => {
    setEditingAsset(asset);

    setAssetForm({
      asset_code: asset.asset_code,
      name: asset.name,
      asset_type: asset.asset_type,
      location: asset.location,
      latitude: asset.latitude != null ? String(asset.latitude) : "",
      longitude: asset.longitude != null ? String(asset.longitude) : "",
      construction_year: asset.construction_year
        ? String(asset.construction_year)
        : "",
      material: asset.material,
      department: asset.department,
      inspection_frequency: asset.inspection_frequency,
    });

    setAssetError("");
    setAssetSuccess("");
    setShowAssetForm(true);
  };

  const handleAssetFormChange = (
    field: keyof AssetForm,
    value: string
  ) => {
    setAssetForm((previous) => ({
      ...previous,
      [field]: value,
    }));
  };

  // Create or update an asset
  const handleAssetSubmit = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    const token = sessionStorage.getItem("access_token");

    if (!token) {
      setAssetError("Please sign in again.");
      return;
    }

    setAssetSaving(true);
    setAssetError("");
    setAssetSuccess("");

    const payload = {
      asset_code: assetForm.asset_code.trim(),
      name: assetForm.name.trim(),
      asset_type: assetForm.asset_type,
      location: assetForm.location.trim(),
      latitude: assetForm.latitude.trim()
  ? Number(assetForm.latitude)
  : null,
longitude: assetForm.longitude.trim()
  ? Number(assetForm.longitude)
  : null,
      construction_year: assetForm.construction_year
        ? Number(assetForm.construction_year)
        : null,
      material: assetForm.material.trim(),
      department: assetForm.department.trim(),
      inspection_frequency: assetForm.inspection_frequency,
    };

    try {
      const isEditing = Boolean(editingAsset);

      const url = isEditing
        ? `${API_BASE_URL}/assets/${editingAsset!.id}`
        : `${API_BASE_URL}/assets/`;

      const response = await fetch(url, {
        method: isEditing ? "PUT" : "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to save asset.");
      }

      setShowAssetForm(false);
      setEditingAsset(null);
      setAssetForm(emptyAssetForm);

      setAssetSuccess(
        isEditing
          ? "Asset updated successfully."
          : "Asset created successfully."
      );

      await fetchAssets(assetSearch);
    } catch (err) {
      setAssetError(
        err instanceof Error
          ? err.message
          : "Unable to save asset."
      );
    } finally {
      setAssetSaving(false);
    }
  };

  // Delete an asset
  const handleDeleteAsset = async (asset: Asset) => {
    if (!canDeleteAssets) return;

    const confirmed = window.confirm(
      `Are you sure you want to delete ${asset.name} (${asset.asset_code})?`
    );

    if (!confirmed) return;

    const token = sessionStorage.getItem("access_token");

    if (!token) {
      setAssetError("Please sign in again.");
      return;
    }

    setAssetError("");
    setAssetSuccess("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/assets/${asset.id}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to delete asset.");
      }

      setAssetSuccess("Asset deleted successfully.");
      await fetchAssets(assetSearch);
    } catch (err) {
      setAssetError(
        err instanceof Error
          ? err.message
          : "Unable to delete asset."
      );
    }
  };

  const visibleNavigation = navigation.filter(
    (item) => !item.adminOnly || user?.role === "Admin"
  );
    if (!user) {
    return (
      <main className="login-page">
        <section className="login-visual">
          <div className="brand">
            <div className="brand-icon">IS</div>
            <span>InfraScan</span>
          </div>

          <div className="visual-content">
            <span className="eyebrow">
              INTELLIGENT INFRASTRUCTURE MONITORING
            </span>
            <h1>
              Building safer
              <br />
              infrastructure
              <br />
              with <span>AI.</span>
            </h1>
            <p>
              Detect, analyze and monitor infrastructure damage using
              intelligent AI-powered inspection technology.
            </p>
            <div className="visual-stats">
              <div>
                <strong>AI</strong>
                <span>Powered analysis</span>
              </div>
              <div>
                <strong>24/7</strong>
                <span>Infrastructure monitoring</span>
              </div>
            </div>
          </div>

          <div className="visual-footer">
            © 2026 InfraScan · Intelligent Infrastructure Assessment
          </div>
        </section>

        <section className="login-panel">
          <div className="login-card">
            <div className="mobile-brand">
              <div className="brand-icon">IS</div>
              <span>InfraScan</span>
            </div>

            <span className="welcome-label">WELCOME BACK</span>
            <h2>Sign in to InfraScan</h2>
            <p className="login-description">
              Enter your credentials to access your workspace.
            </p>

            <form onSubmit={handleLogin}>
              <label htmlFor="role">Select your role</label>
              <select
                id="role"
                value={role}
                onChange={(event) => setRole(event.target.value)}
                disabled={loading}
              >
                {roles.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>

              <label htmlFor="email">Email address</label>
              <input
                id="email"
                type="email"
                placeholder="name@example.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="username"
                required
                disabled={loading}
              />

              <div className="password-heading">
                <label htmlFor="password">Password</label>
              </div>

              <div className="password-field">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="current-password"
                  required
                  disabled={loading}
                />
                <button
                  type="button"
                  className="show-password"
                  onClick={() => setShowPassword((previous) => !previous)}
                  disabled={loading}
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>

              {error && (
                <p className="login-error" role="alert">
                  {error}
                </p>
              )}

              <button
                type="submit"
                className="login-button"
                disabled={loading}
              >
                {loading ? "Signing in..." : "Sign in"}
                {!loading && <span> →</span>}
              </button>
            </form>

            <div className="login-note">
              <span>🔒</span>
              Secure access to your infrastructure workspace
            </div>
          </div>
        </section>
      </main>
    );
  }

  return (
    <div className="dashboard-layout">
      {sidebarOpen && (
        <button
          className="sidebar-backdrop"
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={`dashboard-sidebar ${
          sidebarOpen ? "sidebar-open" : ""
        }`}
      >
        <div className="dashboard-brand">
          <div className="brand-icon">IS</div>
          <div>
            <strong>InfraScan</strong>
            <span>Infrastructure Intelligence</span>
          </div>
        </div>

        <div className="sidebar-section-label">WORKSPACE</div>

        <nav className="dashboard-nav">
          {visibleNavigation.map((item) => (
            <button
              key={item.name}
              className={`nav-item ${
                activePage === item.name ? "active" : ""
              }`}
              onClick={() => {
                setActivePage(item.name);
                setSidebarOpen(false);
              }}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.name}</span>
              {activePage === item.name && (
                <span className="nav-indicator" />
              )}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-help">
            <span className="help-icon">?</span>
            <div>
              <strong>Need assistance?</strong>
              <span>Contact your system administrator</span>
            </div>
          </div>
          <div className="sidebar-version">
            InfraScan · Version 1.0
          </div>
        </div>
      </aside>

      <main className="dashboard-main">
        <header className="dashboard-header">
          <div className="header-left">
            <button
              className="mobile-menu-button"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open navigation"
            >
              ☰
            </button>
            <div>
              <span className="header-breadcrumb">
                WORKSPACE / {activePage.toUpperCase()}
              </span>
              <h2>{activePage}</h2>
            </div>
          </div>

          <div className="header-right">
            <div className="header-user">
             <div className="user-avatar">
  {user.full_name.charAt(0).toUpperCase()}
</div>
<div className="user-details">
  <strong>{user.full_name}</strong>
  <span>{user.role}</span>
</div>
            
            </div>

            <div style={{ position: "relative" }}>
              <button
                type="button"
                onClick={() => setShowNotifications((previous) => !previous)}
                aria-label="Notifications"
                style={{
                  position: "relative",
                  border: "1px solid #e2e8f0",
                  background: "#ffffff",
                  borderRadius: "10px",
                  width: "42px",
                  height: "42px",
                  cursor: "pointer",
                  fontSize: "20px",
                }}
              >
                🔔
                {unreadNotificationCount > 0 && (
                  <span
                    style={{
                      position: "absolute",
                      top: "-6px",
                      right: "-6px",
                      background: "#ef4444",
                      color: "#ffffff",
                      borderRadius: "50%",
                      minWidth: "19px",
                      height: "19px",
                      fontSize: "11px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    {unreadNotificationCount}
                  </span>
                )}
              </button>

              {showNotifications && (
                <div
                  style={{
                    position: "absolute",
                    top: "50px",
                    right: 0,
                    width: "320px",
                    maxHeight: "350px",
                    overflowY: "auto",
                    background: "#ffffff",
                    border: "1px solid #e2e8f0",
                    borderRadius: "12px",
                    boxShadow: "0 8px 25px rgba(0,0,0,0.12)",
                    zIndex: 1000,
                    padding: "16px",
                  }}
                >
                  <h3 style={{ margin: "0 0 12px", color: "#173b55" }}>
                    Notifications
                  </h3>

                  {notifications.length === 0 ? (
                    <p style={{ color: "#64748b", fontSize: "13px" }}>
                      No notifications available.
                    </p>
                  ) : (
                    notifications.map((notification) => (
                      <div
                        key={notification.id}
                        onClick={() =>
                          setReadNotificationIds((previous) =>
                            previous.includes(notification.id)
                              ? previous
                              : [...previous, notification.id]
                          )
                        }
                        style={{
                          padding: "12px 0",
                          borderTop: "1px solid #edf1f5",
                          cursor: "pointer",
                          background: readNotificationIds.includes(notification.id)
                            ? "#ffffff"
                            : "#f0fdfa",
                        }}
                      >
                        <strong style={{ fontSize: "13px", color: "#dc2626" }}>
                          {notification.title}
                        </strong>
                        <p style={{ fontSize: "12px", margin: "6px 0", color: "#475569" }}>
                          {notification.message}
                        </p>
                        <span style={{ fontSize: "11px", color: "#94a3b8" }}>
                          {notification.date}
                        </span>
                        {!readNotificationIds.includes(notification.id) && (
                          <span style={{ fontSize: "11px", color: "#0d9488", marginLeft: "8px" }}>
                            New
                          </span>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            <button className="logout-button" onClick={handleLogout}>

              Logout ↗
            </button>
          </div>
        </header>

        <div className="dashboard-content">
          {activePage === "Overview" && (
            <>
              <section className="dashboard-welcome">
                <div>
                  <span className="dashboard-eyebrow">
                    INFRASTRUCTURE OVERVIEW
                  </span>
                  <h1>
                   Welcome to InfraScan
                  </h1>
                  <p>
                    Monitor infrastructure assets, inspections and
                    AI-powered damage assessments from one workspace.
                  </p>
                </div>
              </section>

              <section className="stat-grid">
                <article className="stat-card">
                  <div className="stat-card-top">
                    <span>Total Assets</span>
                    <span className="stat-icon teal">▤</span>
                  </div>
                  <strong>{assets.length}</strong>
                  <span className="stat-caption">
                    Open Assets to view live records
                  </span>
                  <span className="stat-trend">
                    Live asset count available in Assets
                  </span>
                </article>

                <article className="stat-card">
                  <div className="stat-card-top">
                    <span>Total Inspections</span>
                    <span className="stat-icon blue">⌕</span>
                  </div>
                  <strong>{inspectionRecords.length}</strong>
                  <span className="stat-caption">
                    Inspection records
                  </span>
                  <span className="stat-trend">
                    	AI Analyses
                  </span>
                </article>

                <article className="stat-card">
                  <div className="stat-card-top">
                    <span>AI Analyses</span>
                    <span className="stat-icon orange">◈</span>
                  </div>
                  <strong>{analysisHistory.length}</strong>
                  <span className="stat-caption">
                    Saved AI analysis records
                  </span>
                  <span className="stat-trend">
                    Live saved analysis records
                  </span>
                </article>

                <article className="stat-card">
                  <div className="stat-card-top">
                    <span>Scheduled Inspections</span>
                    <span className="stat-icon purple">◷</span>
                  </div>
                  <strong>{inspectionRecords.filter((item) => item.status === "Scheduled").length}</strong>
                  <span className="stat-caption">
                    Inspections marked as scheduled
                  </span>
                  <span className="stat-trend">
                    Live inspection status count
                  </span>
                </article>
              </section>

              <section className="dashboard-middle-grid">
                
<article className="dashboard-panel damage-panel">
  <div className="panel-heading">
    <div>
      <h3>AI Analysis Summary</h3>
      <p>Saved infrastructure damage analyses</p>
    </div>
  </div>

  <div className="priority-summary">
    <div className="priority-number">
      <strong>{analysisHistory.length}</strong>
      <span>Total analyses</span>
    </div>

    <div className="priority-number">
      <strong>
        {analysisHistory.length > 0
          ? (
              analysisHistory.reduce(
                (total, item) => total + item.crack_percentage,
                0
              ) / analysisHistory.length
            ).toFixed(2) + "%"
          : "—"}
      </strong>
      <span>Average crack pixel percentage</span>
    </div>
  </div>

<div style={{ marginTop: "28px" }}>
  <div style={{
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "20px"
  }}>
    <div>
      <h4 style={{ margin: 0, fontSize: "17px", color: "#173b55" }}>
        Crack Detection Analysis
      </h4>
      <p style={{ margin: "5px 0 0", fontSize: "12px", color: "#8192a5" }}>
        Crack pixel percentage by analyzed image
      </p>
    </div>
    <span style={{
      background: "#e7f5f3",
      color: "#0d9488",
      padding: "7px 12px",
      borderRadius: "20px",
      fontSize: "12px",
      fontWeight: 600
    }}>
      {analysisHistory.length} Records
    </span>
  </div>

  {analysisHistory.length > 0 ? (
    <div style={{
      maxHeight: "360px",
      overflowY: "auto",
      padding: "4px 12px 4px 0"
    }}>
      {analysisHistory.map((item) => {
        const maxValue = Math.max(
          ...analysisHistory.map((record) => record.crack_percentage),
          1
        );

        return (
          <div key={item.id} style={{
            display: "grid",
            gridTemplateColumns: "minmax(100px, 1fr) 2fr 65px",
            alignItems: "center",
            gap: "14px",
            padding: "13px 0",
            borderBottom: "1px solid #edf1f5"
          }}>
            <span style={{
              fontSize: "12px",
              color: "#52677c",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap"
            }} title={item.filename}>
              {item.filename}
            </span>

            <div style={{
              height: "13px",
              background: "#edf2f7",
              borderRadius: "20px",
              overflow: "hidden"
            }}>
              <div style={{
                width: `${Math.min(
                  (item.crack_percentage / maxValue) * 100,
                  100
                )}%`,
                height: "100%",
                background: "linear-gradient(90deg, #0d9488, #38b2ac)",
                borderRadius: "20px",
                transition: "width 0.4s ease"
              }} />
            </div>

            <strong style={{
              fontSize: "13px",
              color: "#173b55",
              textAlign: "right"
            }}>
              {item.crack_percentage.toFixed(2)}%
            </strong>
          </div>
        );
      })}
    </div>
  ) : (
    <p>No saved AI analysis records available.</p>
  )}
</div>


  <p className="demo-note">
    Graph displays crack pixel percentages from saved AI analysis
    records. These values are not structural severity measurements.
  </p>
</article>

<article className="dashboard-panel priority-panel">
  <div className="panel-heading">
    <div>
      <h3>Asset Overview</h3>
      <p>Registered infrastructure assets</p>
    </div>
  </div>

  <div className="priority-summary">
    <div className="priority-number">
      <strong>{assets.length}</strong>
      <span>Total Assets</span>
    </div>

    <div className="priority-number">
      <strong>
        {assets.filter(
          (item) =>
            item.latitude != null && item.longitude != null
        ).length}
      </strong>
      <span>GPS Located Assets</span>
    </div>
  </div>

  <div style={{ marginTop: "28px" }}>
    <h4 style={{ fontSize: "16px", color: "#173b55" }}>
      Assets by Type
    </h4>

    {assets.length > 0 ? (
      Array.from(
        new Set(assets.map((item) => item.asset_type))
      ).map((type) => {
        const count = assets.filter(
          (item) => item.asset_type === type
        ).length;

        return (
          <div key={type} style={{ marginBottom: "20px" }}>
            <div style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: "8px",
              fontSize: "13px"
            }}>
              <span>{type}</span>
              <strong>{count}</strong>
            </div>

            <div style={{
              height: "12px",
              background: "#edf2f7",
              borderRadius: "20px",
              overflow: "hidden"
            }}>
              <div style={{
                width: `${(count / assets.length) * 100}%`,
                height: "100%",
                background: "#0d9488",
                borderRadius: "20px"
              }} />
            </div>
          </div>
        );
      })
    ) : (
      <p>No registered assets available.</p>
    )}
  </div>

  <div className="priority-message">
    <span>ⓘ</span>
    <p>
      Assets without GPS coordinates are not displayed
      on the infrastructure map.
    </p>
  </div>
</article>

              </section>

              <section className="dashboard-panel inspections-panel">
                <div className="panel-heading">
                  <div>
                    <h3>Recent inspections</h3>
                    <p>Latest saved inspection activity</p>
                  </div>
                  <button
                    className="text-action"
                    onClick={() => setActivePage("Inspections")}
                  >
                    View all →
                  </button>
                </div>

                <div className="table-scroll">
                  <table className="inspection-table">
                    <thead>
                      <tr>
                        <th>Inspection ID</th>
                        <th>Asset</th>
                        <th>Type</th>
                        <th>Date</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                   
<tbody>
  {inspectionRecords.length > 0 ? (
    inspectionRecords.slice(0, 5).map((item) => (
      <tr key={item.id}>
        <td className="inspection-id">
          {item.inspection_code}
        </td>
        <td>{item.asset_name}</td>
        <td>{item.inspection_type}</td>
        <td>{item.inspection_date}</td>
        <td>
          <span
            className={`status-pill ${item.status
              .toLowerCase()
              .replace(" ", "-")}`}
          >
            {item.status}
          </span>
        </td>
      </tr>
    ))
  ) : (
    <tr>
      <td colSpan={5}>No inspection records available.</td>
    </tr>
  )}
</tbody>
</table>
</div>

              </section>
            </>
          )}

          {/* ASSET MANAGEMENT */}
          {activePage === "Assets" && (
            <section className="asset-module">
              <div className="asset-page-heading">
                <div>
                  <span className="dashboard-eyebrow">
                    INFRASTRUCTURE MANAGEMENT
                  </span>
                  <h1>Infrastructure Assets</h1>
                  <p>
                    View and manage registered buildings, bridges, roads
                    and other infrastructure.
                  </p>
                </div>

                {canManageAssets && (
                  <button
                    className="asset-primary-button"
                    onClick={openAddAssetForm}
                  >
                    + Add New Asset
                  </button>
                )}
              </div>

              <div className="asset-summary-card">
                <div>
                  <span>Total registered assets</span>
                  <strong>{assets.length}</strong>
                </div>
                <span className="asset-summary-icon">▤</span>
              </div>

              {assetSuccess && (
                <div className="asset-alert asset-alert-success" role="status">
                  {assetSuccess}
                </div>
              )}

              {assetError && !showAssetForm && (
                <div className="asset-alert asset-alert-error" role="alert">
                  {assetError}
                </div>
              )}

              <section className="dashboard-panel asset-list-panel">
                <div className="asset-toolbar">
                  <div>
                    <h3>Registered Assets</h3>
                    <p>Asset records retrieved from the database</p>
                  </div>

                  <form
                    className="asset-search-form"
                    onSubmit={handleSearch}
                  >
                    <input
                      type="search"
                      placeholder="Search assets..."
                      value={assetSearch}
                      onChange={(event) =>
                        setAssetSearch(event.target.value)
                      }
                    />
                    <button type="submit">Search</button>
                  </form>
                </div>

                {assetsLoading ? (
                  <div className="asset-empty-state">
                    Loading assets...
                  </div>
                ) : assets.length === 0 ? (
                  <div className="asset-empty-state">
                    <div className="placeholder-icon">▤</div>
                    <h3>No assets found</h3>
                    <p>
                      {assetSearch
                        ? "Try another search term."
                        : "Add your first infrastructure asset to get started."}
                    </p>
                    {canManageAssets && !assetSearch && (
                      <button
                        className="asset-primary-button"
                        onClick={openAddAssetForm}
                      >
                        + Add New Asset
                      </button>
                    )}
                  </div>
                ) : (
                  
<div className="table-scroll">
  <table className="inspection-table">
    <thead>
      <tr>
        <th>Asset Code</th>
        <th>Asset Name</th>
        <th>Type</th>
        <th>Location</th>
        <th>Department</th>
        <th>Actions</th>
      </tr>
    </thead>

    <tbody>
      {assets.map((asset) => (
        <tr key={asset.id}>
          <td className="inspection-id">{asset.asset_code}</td>
          <td>{asset.name}</td>
          <td>{asset.asset_type}</td>
          <td>{asset.location}</td>
          <td>{asset.department}</td>
          <td>
            {canManageAssets && (
              <button
                type="button"
                onClick={() => openEditAssetForm(asset)}
              >
                Edit
              </button>
            )}

            {canDeleteAssets && (
              <button
                type="button"
                onClick={() => handleDeleteAsset(asset)}
              >
                Delete
              </button>
            )}
          </td>
        </tr>
      ))}
    </tbody>
  </table>
</div>

                )}

                <div className="asset-list-footer">
                  Showing {assets.length} saved asset
                  {assets.length === 1 ? "" : "s"}
                </div>
              </section>

              {/* ADD / EDIT ASSET FORM */}
              {showAssetForm && (
                <div className="asset-modal-backdrop">
                  <section
                    className="asset-modal"
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="asset-form-title"
                  >
                    <div className="asset-modal-heading">
                      <div>
                        <span className="dashboard-eyebrow">
                          ASSET INFORMATION
                        </span>
                        <h2 id="asset-form-title">
                          {editingAsset ? "Edit Asset" : "Add New Asset"}
                        </h2>
                        <p>
                          Enter the infrastructure asset details below.
                        </p>
                      </div>

                      <button
                        type="button"
                        className="asset-close-button"
                        onClick={() => {
                          setShowAssetForm(false);
                          setAssetError("");
                        }}
                        aria-label="Close form"
                      >
                        ×
                      </button>
                    </div>

                    {assetError && (
                      <div
                        className="asset-alert asset-alert-error"
                        role="alert"
                      >
                        {assetError}
                      </div>
                    )}

                    <form
                      className="asset-form"
                      onSubmit={handleAssetSubmit}
                    >
                      <div className="asset-form-grid">
                        <label>
                          Asset ID
                          <input
                            required
                            value={assetForm.asset_code}
                            onChange={(event) =>
                              handleAssetFormChange(
                                "asset_code",
                                event.target.value
                              )
                            }
                            placeholder="e.g. INF-BRG-002"
                            maxLength={30}
                          />
                        </label>

                        <label>
                          Asset Name
                          <input
                            required
                            value={assetForm.name}
                            onChange={(event) =>
                              handleAssetFormChange(
                                "name",
                                event.target.value
                              )
                            }
                            placeholder="Enter asset name"
                            maxLength={120}
                          />
                        </label>

                        <label>
                          Asset Type
                          <select
                            value={assetForm.asset_type}
                            onChange={(event) =>
                              handleAssetFormChange(
                                "asset_type",
                                event.target.value
                              )
                            }
                          >
                            <option>Building</option>
                            <option>Bridge</option>
                            <option>Road</option>
                            <option>Tunnel</option>
                            <option>Dam</option>
                            <option>Concrete Structure</option>
                            <option>Retaining Wall</option>
                            <option>Industrial Structure</option>
                          </select>
                        </label>

                        <label>
                          Location
                          <input
                            required
                            value={assetForm.location}
                            onChange={(event) =>
                              handleAssetFormChange(
                                "location",
                                event.target.value
                              )
                            }
                            placeholder="City, State"
                            maxLength={200}
                          />
                        </label>
                        <label>
  Latitude
  <input
    type="number"
    step="any"
    min="-90"
    max="90"
    value={assetForm.latitude}
    onChange={(event) =>
      handleAssetFormChange("latitude", event.target.value)
    }
    placeholder="e.g. 12.2958"
  />
</label>

<label>
  Longitude
  <input
    type="number"
    step="any"
    min="-180"
    max="180"
    value={assetForm.longitude}
    onChange={(event) =>
      handleAssetFormChange("longitude", event.target.value)
    }
    placeholder="e.g. 76.6394"
  />
</label>

                        <label>
                          Construction Year
                          <input
                            type="number"
                            min="1800"
                            max="2100"
                            value={assetForm.construction_year}
                            onChange={(event) =>
                              handleAssetFormChange(
                                "construction_year",
                                event.target.value
                              )
                            }
                            placeholder="e.g. 2018"
                          />
                        </label>

                        <label>
                          Material
                          <input
                            required
                            value={assetForm.material}
                            onChange={(event) =>
                              handleAssetFormChange(
                                "material",
                                event.target.value
                              )
                            }
                            placeholder="e.g. Reinforced Concrete"
                            maxLength={80}
                          />
                        </label>

                        <label>
                          Department
                          <input
                            required
                            value={assetForm.department}
                            onChange={(event) =>
                              handleAssetFormChange(
                                "department",
                                event.target.value
                              )
                            }
                            placeholder="Enter department"
                            maxLength={100}
                          />
                        </label>

                        <label>
                          Inspection Frequency
                          <select
                            value={assetForm.inspection_frequency}
                            onChange={(event) =>
                              handleAssetFormChange(
                                "inspection_frequency",
                                event.target.value
                              )
                            }
                          >
                            <option>Every 3 Months</option>
                            <option>Every 6 Months</option>
                            <option>Every 12 Months</option>
                            <option>Annually</option>
                            <option>As Required</option>
                          </select>
                        </label>
                      </div>

                      <div className="asset-form-actions">
                        <button
                          type="button"
                          className="asset-cancel-button"
                          onClick={() => {
                            setShowAssetForm(false);
                            setAssetError("");
                          }}
                          disabled={assetSaving}
                        >
                          Cancel
                        </button>

                        <button
                          type="submit"
                          className="asset-primary-button"
                          disabled={assetSaving}
                        >
                          {assetSaving
                            ? "Saving..."
                            : editingAsset
                              ? "Update Asset"
                              : "Save Asset"}
                        </button>
                      </div>
                    </form>
                  </section>
                </div>
              )}
            </section>
          )}
                    {/* INSPECTION MANAGEMENT */}
          {activePage === "Inspections" && (
            <section className="inspection-module">
              <div className="inspection-page-heading">
                <div>
                  <span className="dashboard-eyebrow">
                    INFRASTRUCTURE MONITORING
                  </span>
                  <h1>Inspection Management</h1>
                  <p>
                    Schedule, track and manage infrastructure inspections.
                  </p>
                </div>

                {canManageInspections && (
                  <button
                    className="asset-primary-button"
                    onClick={openAddInspectionForm}
                  >
                    + Schedule Inspection
                  </button>
                )}
              </div>

              <div className="inspection-summary-grid">
                <article className="inspection-summary-card">
                  <span>Total Inspections</span>
                  <strong>{inspectionRecords.length}</strong>
                  <small>Saved inspection records</small>
                </article>

                <article className="inspection-summary-card">
                  <span>Scheduled</span>
                  <strong>
                    {inspectionRecords.filter(
                      (item) => item.status === "Scheduled"
                    ).length}
                  </strong>
                  <small>Awaiting inspection</small>
                </article>

                <article className="inspection-summary-card">
                  <span>In Progress</span>
                  <strong>
                    {inspectionRecords.filter(
                      (item) => item.status === "In Progress"
                    ).length}
                  </strong>
                  <small>Currently ongoing</small>
                </article>

                <article className="inspection-summary-card">
                  <span>Completed</span>
                  <strong>
                    {inspectionRecords.filter(
                      (item) => item.status === "Completed"
                    ).length}
                  </strong>
                  <small>Completed inspections</small>
                </article>
              </div>

              {inspectionSuccess && (
                <div
                  className="asset-alert asset-alert-success"
                  role="status"
                >
                  {inspectionSuccess}
                </div>
              )}

              {inspectionError && !showInspectionForm && (
                <div
                  className="asset-alert asset-alert-error"
                  role="alert"
                >
                  {inspectionError}
                </div>
              )}

              <section className="dashboard-panel inspection-list-panel">
                <div className="inspection-toolbar">
                  <div>
                    <h3>Inspection Records</h3>
                    <p>Live records retrieved from the database</p>
                  </div>

                  <form
                    className="asset-search-form"
                    onSubmit={handleInspectionSearch}
                  >
                    <input
                      type="search"
                      placeholder="Search inspections..."
                      value={inspectionSearch}
                      onChange={(event) =>
                        setInspectionSearch(event.target.value)
                      }
                    />

                    <select
                      value={inspectionStatusFilter}
                      onChange={(event) => {
                        setInspectionStatusFilter(event.target.value);
                        fetchInspections(
                          inspectionSearch,
                          event.target.value
                        );
                      }}
                    >
                      <option value="">All Statuses</option>
                      <option value="Scheduled">Scheduled</option>
                      <option value="In Progress">In Progress</option>
                      <option value="Completed">Completed</option>
                      <option value="Cancelled">Cancelled</option>
                    </select>

                    <button type="submit">Search</button>
                  </form>
                </div>

                {inspectionsLoading ? (
                  <div className="asset-empty-state">
                    Loading inspections...
                  </div>
                ) : inspectionRecords.length === 0 ? (
                  <div className="asset-empty-state">
                    <div className="placeholder-icon">⌕</div>
                    <h3>No inspections found</h3>
                    <p>
                      {inspectionSearch || inspectionStatusFilter
                        ? "Try changing your search or filter."
                        : "Schedule your first infrastructure inspection."}
                    </p>
                    {canManageInspections &&
                      !inspectionSearch &&
                      !inspectionStatusFilter && (
                        <button
                          className="asset-primary-button"
                          onClick={openAddInspectionForm}
                        >
                          + Schedule Inspection
                        </button>
                      )}
                  </div>
                ) : (
                  <div className="table-scroll">
                    <table className="inspection-table">
                      <thead>
                        <tr>
                          <th>Inspection ID</th>
                          <th>Asset</th>
                          <th>Inspection Type</th>
                          <th>Date</th>
                          <th>Inspector</th>
                          <th>Status</th>
                          <th>Actions</th>
                        </tr>
                      </thead>

                      <tbody>
                        {inspectionRecords.map((inspection) => (
                          <tr key={inspection.id}>
                            <td className="inspection-id">
                              <strong>
                                {inspection.inspection_code}
                              </strong>
                            </td>

                            <td>
                              <strong>{inspection.asset_name}</strong>
                              <small className="inspection-subtext">
                                {inspection.asset_code}
                              </small>
                            </td>

                            <td>{inspection.inspection_type}</td>

                            <td>
                              {new Date(
                                `${inspection.inspection_date}T00:00:00`
                              ).toLocaleDateString("en-IN", {
                                day: "2-digit",
                                month: "long",
                                year: "numeric",
                              })}
                            </td>

                            <td>
                              {inspection.inspector_name || "Not assigned"}
                            </td>

                            <td>
                              <span
                                className={`status-pill ${inspection.status
                                  .toLowerCase()
                                  .replace(" ", "-")}`}
                              >
                                {inspection.status}
                              </span>
                            </td>

                            <td>
                              <div className="asset-actions">
                                {canManageInspections && (
                                  <button
                                    type="button"
                                    className="asset-edit-button"
                                    onClick={() =>
                                      openEditInspectionForm(inspection)
                                    }
                                  >
                                    Edit
                                  </button>
                                )}

                                {canDeleteInspections && (
                                  <button
                                    type="button"
                                    className="asset-delete-button"
                                    onClick={() =>
                                      handleDeleteInspection(inspection)
                                    }
                                  >
                                    Delete
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                <div className="asset-list-footer">
                  Showing {inspectionRecords.length} saved inspection
                  {inspectionRecords.length === 1 ? "" : "s"}
                </div>
              </section>

              {/* CREATE / EDIT INSPECTION FORM */}
              {showInspectionForm && (
                <div className="asset-modal-backdrop">
                  <section
                    className="asset-modal"
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="inspection-form-title"
                  >
                    <div className="asset-modal-heading">
                      <div>
                        <span className="dashboard-eyebrow">
                          INSPECTION INFORMATION
                        </span>

                        <h2 id="inspection-form-title">
                          {editingInspection
                            ? "Edit Inspection"
                            : "Schedule New Inspection"}
                        </h2>

                        <p>
                          Enter the inspection details below.
                        </p>
                      </div>

                      <button
                        type="button"
                        className="asset-close-button"
                        onClick={() => {
                          setShowInspectionForm(false);
                          setInspectionError("");
                        }}
                        aria-label="Close form"
                      >
                        ×
                      </button>
                    </div>

                    {inspectionError && (
                      <div
                        className="asset-alert asset-alert-error"
                        role="alert"
                      >
                        {inspectionError}
                      </div>
                    )}

                    <form
                      className="asset-form"
                      onSubmit={handleInspectionSubmit}
                    >
                      <div className="asset-form-grid">
                        <label>
                          Inspection ID
                          <input
                            required
                            value={inspectionForm.inspection_code}
                            onChange={(event) =>
                              handleInspectionFormChange(
                                "inspection_code",
                                event.target.value
                              )
                            }
                            placeholder="e.g. INS-2026-002"
                            maxLength={40}
                            minLength={3}
                          />
                        </label>

                        <label>
                          Select Infrastructure Asset
                          <select
                            required
                            value={inspectionForm.asset_id}
                            onChange={(event) =>
                              handleInspectionFormChange(
                                "asset_id",
                                event.target.value
                              )
                            }
                          >
                            <option value="">Select an asset</option>
                            {assets.map((asset) => (
                              <option
                                key={asset.id}
                                value={asset.id}
                              >
                                {asset.asset_code} - {asset.name}
                              </option>
                            ))}
                          </select>
                        </label>

                        <label>
                          Inspection Date
                          <input
                            type="date"
                            required
                            value={inspectionForm.inspection_date}
                            onChange={(event) =>
                              handleInspectionFormChange(
                                "inspection_date",
                                event.target.value
                              )
                            }
                          />
                        </label>

                        <label>
                          Inspection Type
                          <select
                            required
                            value={inspectionForm.inspection_type}
                            onChange={(event) =>
                              handleInspectionFormChange(
                                "inspection_type",
                                event.target.value
                              )
                            }
                          >
                            <option>Routine Visual Inspection</option>
                            <option>Detailed Structural Inspection</option>
                            <option>Preventive Inspection</option>
                            <option>Emergency Inspection</option>
                            <option>Follow-up Inspection</option>
                          </select>
                        </label>

                        <label>
                          Assign Inspector
                          <select
                            value={inspectionForm.assigned_inspector_id}
                            onChange={(event) =>
                              handleInspectionFormChange(
                                "assigned_inspector_id",
                                event.target.value
                              )
                            }
                          >
                            <option value="">Not assigned</option>

                            {inspectors.map((inspector) => (
                              <option
                                key={inspector.id}
                                value={inspector.id}
                              >
                                {inspector.full_name} ({inspector.role})
                              </option>
                            ))}
                          </select>

                          {inspectors.length === 0 && (
                            <small className="inspection-help-text">
                              No active inspectors are registered yet.
                            </small>
                          )}
                        </label>

                        <label>
                          Inspection Status
                          <select
                            value={inspectionForm.status}
                            onChange={(event) =>
                              handleInspectionFormChange(
                                "status",
                                event.target.value
                              )
                            }
                          >
                            <option value="Scheduled">Scheduled</option>
                            <option value="In Progress">In Progress</option>
                            <option value="Completed">Completed</option>
                            <option value="Cancelled">Cancelled</option>
                          </select>
                        </label>

                        <label className="inspection-notes-field">
                          Notes
                          <textarea
                            value={inspectionForm.notes}
                            onChange={(event) =>
                              handleInspectionFormChange(
                                "notes",
                                event.target.value
                              )
                            }
                            placeholder="Enter inspection notes..."
                            rows={4}
                            maxLength={2000}
                          />
                        </label>
                      </div>

                      <div className="asset-form-actions">
                        <button
                          type="button"
                          className="asset-cancel-button"
                          onClick={() => {
                            setShowInspectionForm(false);
                            setInspectionError("");
                          }}
                          disabled={inspectionSaving}
                        >
                          Cancel
                        </button>

                        <button
                          type="submit"
                          className="asset-primary-button"
                          disabled={
                            inspectionSaving || assets.length === 0
                          }
                        >
                          {inspectionSaving
                            ? "Saving..."
                            : editingInspection
                              ? "Update Inspection"
                              : "Save Inspection"}
                        </button>
                      </div>
                    </form>
                  </section>
                </div>
              )}
            </section>
          )}
{activePage === "AI Damage Analysis" && (
  <section className="ai-analysis-module">
    <div className="page-heading">
      <div>
        <h2>AI Damage Analysis</h2>
        <p>Upload an infrastructure image to detect and analyze cracks.</p>
      </div>
    </div>

    <div className="ai-upload-card">
      <h3>Upload Infrastructure Image</h3>
      <p>Select a clear image of a road, bridge, wall, or other structure.</p>

      <input
        type="file"
        accept="image/*"
        multiple
        onChange={handleImageSelect}
      />

{selectedImages.length > 0 && (
  <div className="ai-selected-images">
    <div className="ai-selected-header">
      <h3>Selected Images</h3>
      <span>{selectedImages.length} images selected</span>
    </div>

    <div className="ai-image-preview-grid">
      {selectedImages.map((image, index) => (
        <div
          className="ai-image-preview-card"
          key={`${image.name}-${index}`}
        >
          <div className="ai-image-thumbnail">
            <img
              src={selectedImagePreviews[index]}
              alt={image.name}
            />

            <button
              type="button"
              className="ai-image-remove-icon"
              onClick={() => handleRemoveSelectedImage(index)}
              disabled={analysisLoading}
              aria-label={`Remove ${image.name}`}
              title="Remove image"
            >
              ×
            </button>
          </div>

          <div className="ai-image-file-info">
            <strong title={image.name}>{image.name}</strong>
            <span>{(image.size / 1024).toFixed(1)} KB</span>
          </div>
        </div>
      ))}
    </div>
  </div>
)}

      {analysisError && (
        <p className="ai-error">{analysisError}</p>
      )}

      <button
        type="button"
        onClick={handleAnalyzeImage}
        disabled={selectedImages.length === 0|| analysisLoading}
      >
        {analysisLoading ? "Analyzing Images..." : "Analyze Images"}
      </button>
     <button
  type="button"
  className="ai-clear-button"
  onClick={handleClearAnalysis}
  disabled={analysisLoading}
>
  Clear Results
</button>

      {analysisLoading && (
        <p>Please wait while the AI model analyzes your image.</p>
      )}
      {multipleAnalysisResults.length > 0 && (
  <div className="ai-summary-grid">
    <div className="ai-summary-card">
      <span>Total Images Analyzed</span>
      <h2>{totalImagesAnalyzed}</h2>
    </div>

    <div className="ai-summary-card">
      <span>Average Crack Percentage</span>
      <h2>{averageCrackPercentage.toFixed(2)}%</h2>
    </div>

    <div className="ai-summary-card">
      <span>Highest Crack Percentage</span>
      <h2>{highestCrackPercentage.toFixed(2)}%</h2>
    </div>

    <div className="ai-summary-card">
      <span>Lowest Crack Percentage</span>
      <h2>{lowestCrackPercentage.toFixed(2)}%</h2>
    </div>
  </div>
)}
{multipleAnalysisResults.map((result, index) => (
  <div className="ai-result-card" key={`${result.filename}-${index}`}>
    <div className="ai-result-header">
      <h3>{result.filename}</h3>
      <span className="ai-result-status">Analysis Successful</span>
    </div>

    <div className="ai-result-details">
      <div className="ai-result-image">
        <h4>Original Image</h4>
        <img
          src={result.originalImage}
          alt={`Original infrastructure image ${result.filename}`}
        />
      </div>

     <div className="ai-result-image">
  <h4>Predicted Crack Mask</h4>
  <img
    src={`data:image/png;base64,${result.mask}`}
    alt={`Predicted crack mask for ${result.filename}`}
  />

  <a
    className="ai-download-mask-button"
    href={`data:image/png;base64,${result.mask}`}
    download={`${result.filename.replace(/\.[^/.]+$/, "")}_crack_mask.png`}
  >
    Download Crack Mask
  </a>
</div>
<div className="ai-result-image">
  <h4>Crack Detection Overlay</h4>

  <img
    src={`data:image/png;base64,${result.overlay}`}
    alt={`Red crack overlay for ${result.filename}`}
  />
</div>

<div className="ai-result-image">
  <h4>Prediction Probability Heatmap</h4>

  <img
    src={`data:image/png;base64,${result.confidence_heatmap}`}
    alt={`Prediction probability heatmap for ${result.filename}`}
  />

  <div
    style={{
      marginTop: "14px",
      padding: "16px",
      background: "#f8fafc",
      border: "1px solid #e2e8f0",
      borderRadius: "8px",
    }}
  >
    <h4 style={{ marginTop: 0 }}>
      Understanding the Heatmap
    </h4>

    <p style={{ fontSize: "13px", color: "#475569" }}>
      This heatmap visualizes the pixel-level prediction
      values generated by the U-Net crack detection model.
    </p>

    <div style={{
      display: "flex",
      flexWrap: "wrap",
      gap: "16px",
      marginTop: "12px",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "7px" }}>
        <span style={{
          width: "15px",
          height: "15px",
          background: "#0000ff",
          borderRadius: "3px",
        }} />
        <span style={{ fontSize: "13px" }}>Blue - Low</span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "7px" }}>
        <span style={{
          width: "15px",
          height: "15px",
          background: "#80ff80",
          borderRadius: "3px",
        }} />
        <span style={{ fontSize: "13px" }}>Green - Intermediate</span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "7px" }}>
        <span style={{
          width: "15px",
          height: "15px",
          background: "#ff0000",
          borderRadius: "3px",
        }} />
        <span style={{ fontSize: "13px" }}>Red - High</span>
      </div>
    </div>

    <p style={{
      fontSize: "12px",
      color: "#64748b",
      marginBottom: 0,
      marginTop: "12px",
    }}>
      Higher prediction values indicate pixels the model
      considers more likely to belong to a crack.
      These are model outputs, not calibrated confidence scores.
    </p>
  </div>
</div>

      <div className="ai-result-percentage">
  <span>Crack Percentage</span>
  <h2>{result.crack_percentage.toFixed(2)}%</h2>

  <div className={`severity-label ${result.severity.toLowerCase()}`}>
    {result.severity} Severity
  </div>

  <p>{result.severity_description}</p>
  <div className="ai-result-dimensions">
  <p>
    Estimated Crack Length: {result.crack_length_pixels} px
  </p>
  <p>
    Estimated Average Crack Width: {result.average_crack_width_pixels} px
  </p>
</div>

  <small>{result.assessment_note}</small>
</div>
    </div>
  </div>
))}
    </div>
  </section>
)}
{activePage === "Damage Reports" && (
  <section className="damage-reports-module">
    <div className="page-heading">
      <div>
        <h2>Damage Reports</h2>
        <p>Review saved AI-generated infrastructure damage analysis results.</p>
      </div>
    </div>

    {historyLoading ? (
      <div className="ai-upload-card">
        <p>Loading saved analysis reports...</p>
      </div>
    ) : historyError ? (
      <div className="asset-alert asset-alert-error">
        {historyError}
      </div>
    ) : analysisHistory.length === 0 ? (
      <div className="ai-upload-card">
        <h3>No Analysis Reports Available</h3>
        <p>
          Analyze infrastructure images to view saved reports here.
        </p>
        <button
          type="button"
          onClick={() => setActivePage("AI Damage Analysis")}
        >
          Go to AI Damage Analysis
        </button>
      </div>
    ) : (
      <>



        <div className="ai-upload-card">
          <h3>Saved Image Analysis Records</h3>
          <button
  type="button"
  className="ai-download-mask-button"
  onClick={handleDownloadDamageReport}
  disabled={analysisHistory.length === 0}
>
  Download PDF Report
</button>
<button
  type="button"
  className="ai-download-mask-button"
  onClick={handleDownloadCSVReport}
  disabled={analysisHistory.length === 0}
  style={{ marginLeft: "10px" }}
>
  Download CSV Report
</button>
<button
  type="button"
  className="ai-download-mask-button"
  onClick={handleDownloadExcelReport}
  disabled={analysisHistory.length === 0}
  style={{ marginLeft: "10px" }}
>
  Download Excel Report
</button>
<div style={{
  display: "flex",
  gap: "10px",
  margin: "20px 0",
  flexWrap: "wrap"
}}>
  <input
    type="text"
    placeholder="Search by image name..."
    value={reportSearch}
    onChange={(e) => setReportSearch(e.target.value)}
    style={{
      flex: 1,
      minWidth: "220px",
      padding: "12px",
      border: "1px solid #cbd5e1",
      borderRadius: "8px"
    }}
  />

  <button
    type="button"
    onClick={() => setAppliedReportSearch(reportSearch)}
  >
    Search
  </button>

  <button
    type="button"
    onClick={() => {
      setReportSearch("");
      setAppliedReportSearch("");
    }}
  >
    Clear
  </button>
</div>

          <div className="damage-report-table-wrapper">
            <table className="damage-report-table">
              <thead>
                <tr>
                  <th>Sl. No.</th>
                  <th>Image Name</th>
                  <th>Crack Pixel Percentage</th>
                  <th>Analysis Date</th>
                  <th>Analysis Status</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {filteredAnalysisHistory.map((record, index) => (
                  <tr key={record.id}>
                    <td>{index + 1}</td>
                    <td className="damage-report-filename">
                      {record.filename}
                    </td>
                    <td className="damage-report-value">
                      {record.crack_percentage.toFixed(2)}%
                    </td>
                    <td>
                      {new Date(
                        record.analyzed_at.replace(" ", "T") + "Z"
                      ).toLocaleString()}
                    </td>
                    
<td>
  <span className="damage-report-status">
    Completed
  </span>
</td>

<td>
  {user?.role === "Admin" && (
    <button
      onClick={() => handleDeleteAnalysis(record.id)}
      style={{
        backgroundColor: "#dc2626",
        color: "white",
        border: "none",
        padding: "6px 12px",
        borderRadius: "5px",
        cursor: "pointer",
      }}
    >
      Delete
    </button>
  )}
</td>
</tr>

                ))}
              </tbody>
            </table>
          </div>
        </div>
      </>
    )}
  </section>
)}

{/* HISTORICAL DAMAGE COMPARISON */}

{activePage === "Historical Comparison" && (
  <section className="asset-module">
    <div className="asset-page-heading">
      <div>
        <span className="dashboard-eyebrow">
          DAMAGE MONITORING
        </span>
        <h1>Historical Damage Comparison</h1>
        <p>
          Compare previous and latest crack analysis results
          for the same image.
        </p>
      </div>
    </div>

    {historyLoading ? (
      <div className="ai-upload-card">
        <p>Loading historical records...</p>
      </div>
    ) : historyError ? (
      <div className="asset-alert asset-alert-error">
        {historyError}
      </div>
    ) : (
      <div className="ai-upload-card">
        <h3>Analysis History</h3>

        {(() => {
          const groupedRecords = new Map<
            string,
            typeof analysisHistory
          >();

          analysisHistory.forEach((record) => {
            const existing =
              groupedRecords.get(record.filename) || [];

            existing.push(record);
            groupedRecords.set(record.filename, existing);
          });

          const comparisons = Array.from(
            groupedRecords.entries()
          )
            .map(([filename, records]) => {
              const sorted = [...records].sort(
                (a, b) =>
                  new Date(
                    b.analyzed_at.replace(" ", "T") + "Z"
                  ).getTime() -
                  new Date(
                    a.analyzed_at.replace(" ", "T") + "Z"
                  ).getTime()
              );

              return {
                filename,
                latest: sorted[0],
                previous: sorted[1],
              };
            })
            

          if (comparisons.length === 0) {
            return (
              <p>
                No previous analysis available yet.
                Analyze the same image again to compare
                historical results.
              </p>
            );
          }
return comparisons.map((item) => {
  const difference = item.previous
    ? item.latest.crack_percentage - item.previous.crack_percentage
    : null;

  return (
    <div
      key={item.filename}
      style={{
        padding: "16px",
        marginTop: "12px",
        border: "1px solid #e2e8f0",
        borderRadius: "8px",
      }}
    >
      <h4>{item.filename}</h4>

      {item.previous ? (
        <>
          <p>Previous: {item.previous.crack_percentage.toFixed(2)}%</p>
          <p>Latest: {item.latest.crack_percentage.toFixed(2)}%</p>

          <strong
            style={{
              color:
                difference! > 0
                  ? "#dc2626"
                  : difference! < 0
                  ? "#16a34a"
                  : "#64748b",
            }}
          >
            {difference! > 0
              ? `Increased by ${difference!.toFixed(2)} percentage points`
              : difference! < 0
              ? `Decreased by ${Math.abs(difference!).toFixed(2)} percentage points`
              : "No change in crack percentage"}
          </strong>
        </>
      ) : (
        <>
          <p>Latest analysis: {item.latest.crack_percentage.toFixed(2)}%</p>
          <strong style={{ color: "#2563eb" }}>
            Waiting for next analysis
          </strong>
        </>
      )}
    </div>
  );
});
        })()}
      </div>
    )}
  </section>
)}

{/* DAMAGE ANALYTICS */}

{activePage === "Damage Analytics" && (
  <section className="asset-module">
    <div className="asset-page-heading">
      <div>
        <span className="dashboard-eyebrow">
          DAMAGE INSIGHTS
        </span>
        <h1>Damage Analytics</h1>
        <p>
          Analyze crack percentage trends from saved AI
          assessment records.
        </p>
      </div>
    </div>

    {historyLoading ? (
      <div className="ai-upload-card">
        <p>Loading damage analytics...</p>
      </div>
    ) : historyError ? (
      <div className="asset-alert asset-alert-error">
        {historyError}
      </div>
    ) : analysisHistory.length === 0 ? (
      <div className="ai-upload-card">
        <h3>No Analysis Data Available</h3>
        <p>
          Analyze infrastructure images to view damage analytics.
        </p>
      </div>
    ) : (
      <>
        <div className="inspection-summary-grid">
          <article className="inspection-summary-card">
            <span>Total Saved Reports</span>
            <strong>{analysisHistory.length}</strong>
          </article>

          <article className="inspection-summary-card">
            <span>Average Crack Percentage</span>
            <strong>
              {(
                analysisHistory.reduce(
                  (sum, item) => sum + item.crack_percentage,
                  0
                ) / analysisHistory.length
              ).toFixed(2)}%
            </strong>
          </article>

          <article className="inspection-summary-card">
            <span>Highest Crack Percentage</span>
            <strong>
              {Math.max(
                ...analysisHistory.map(
                  (item) => item.crack_percentage
                )
              ).toFixed(2)}%
            </strong>
          </article>

          <article className="inspection-summary-card">
            <span>Lowest Crack Percentage</span>
            <strong>
              {Math.min(
                ...analysisHistory.map(
                  (item) => item.crack_percentage
                )
              ).toFixed(2)}%
            </strong>
          </article>
        </div>

        <div className="ai-upload-card">
          <h3>Crack Percentage Analysis</h3>
          <p>
            Comparison of crack pixel percentages across saved
            analysis records.
          </p>

          <div style={{ marginTop: "20px" }}>
            {analysisHistory.map((record) => (
              <div
                key={record.id}
                style={{ marginBottom: "18px" }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: "6px",
                  }}
                >
                  <strong>{record.filename}</strong>
                  <strong>
                    {record.crack_percentage.toFixed(2)}%
                  </strong>
                </div>

                <div
                  style={{
                    width: "100%",
                    height: "14px",
                    backgroundColor: "#e2e8f0",
                    borderRadius: "10px",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${Math.min(
                        record.crack_percentage / 5 * 100,
                        100
                      )}%`,
                      height: "100%",
                      backgroundColor: "#0d9488",
                      borderRadius: "10px",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>

          <p style={{ fontSize: "12px", marginTop: "16px" }}>
            Crack percentages are image-based estimates and
            should not be treated as structural safety ratings.
          </p>
        </div>
      </>
    )}
  </section>
)}


{/* MAINTENANCE PRIORITIZATION */}

{activePage === "Maintenance" && (
  <section className="asset-module">
    <div className="asset-page-heading">
      <div>
        <span className="dashboard-eyebrow">
          INFRASTRUCTURE MAINTENANCE
        </span>
        <h1>Maintenance Prioritization</h1>
        <p>
          Review saved damage reports in descending order of crack percentage.
        </p>
      </div>
    </div>

    <div className="inspection-summary-grid">
      <article className="inspection-summary-card">
        <span>Total Saved Reports</span>
        <strong>{savedMaintenanceRecords.length}</strong>
      </article>

      <article className="inspection-summary-card">
        <span>Highest Crack Percentage</span>
        <strong>
          {savedMaintenanceRecords.length
            ? `${savedMaintenanceRecords[0].crack_percentage.toFixed(2)}%`
            : "0%"}
        </strong>
      </article>

      <article className="inspection-summary-card">
        <span>Lowest Crack Percentage</span>
        <strong>
          {savedMaintenanceRecords.length
            ? `${savedMaintenanceRecords[savedMaintenanceRecords.length - 1].crack_percentage.toFixed(2)}%`
            : "0%"}
        </strong>
      </article>

      <article className="inspection-summary-card">
        <span>Average Crack Percentage</span>
        <strong>
          {savedMaintenanceRecords.length
            ? `${(
                savedMaintenanceRecords.reduce(
                  (sum, item) => sum + item.crack_percentage,
                  0
                ) / savedMaintenanceRecords.length
              ).toFixed(2)}%`
            : "0%"}
        </strong>
      </article>
    </div>

    <div className="ai-upload-card">
      <h3>Maintenance Review Recommendations</h3>

      {savedMaintenanceRecords.length === 0 ? (
        <p>No saved damage reports available.</p>
      ) : (
        savedMaintenanceRecords.map((record, index) => (
          <div
            key={record.id}
            style={{
              padding: "16px",
              marginTop: "12px",
              border: "1px solid #e2e8f0",
              borderRadius: "8px",
            }}
          >
            <h4>{index + 1}. {record.filename}</h4>

            <p>
              Crack Percentage: {record.crack_percentage.toFixed(2)}%
            </p>

            <strong
  style={{
    color:
      record.crack_percentage >= 5
        ? "#dc2626"
        : record.crack_percentage >= 2
        ? "#d97706"
        : "#16a34a",
  }}
>
  {record.crack_percentage >= 5
    ? "High Priority"
    : record.crack_percentage >= 2
    ? "Medium Priority"
    : "Low Priority"}
</strong>

            <p>
              Recommendation: Review this saved report and arrange
              an engineering inspection as appropriate.
            </p>
          </div>
        ))
      )}

      <p style={{ marginTop: "16px", fontSize: "12px" }}>
        Review order is based on crack pixel percentage only.
        It is not a structural safety rating or an automatic
        maintenance decision.
      </p>
    </div>
  </section>
)}

{/* INFRASTRUCTURE MAP */}
{activePage === "Infrastructure Map" && (
  <section className="asset-module">
    <div className="asset-page-heading">
      <div>
        <span className="dashboard-eyebrow">
          INFRASTRUCTURE LOCATION TRACKING
        </span>
        <h1>Infrastructure Map</h1>
        <p>
          View registered infrastructure assets in Mysore, Karnataka.
        </p>
      </div>
    </div>

    <div className="ai-upload-card">
      <h3>Asset Location Map</h3>

      <div style={{
        width: "100%",
        height: "400px",
        borderRadius: "10px",
        overflow: "hidden",
        marginTop: "16px"
      }}>
        <div
  ref={mapContainerRef}
  style={{
    width: "100%",
    height: "100%",
  }}
/>
      </div>

      <p style={{ fontSize: "12px", marginTop: "10px" }}>
  {assets.filter(
    (asset) => asset.latitude != null && asset.longitude != null
  ).length} infrastructure assets displayed on the map.
</p>
    </div>

    <div className="ai-upload-card">
      <h3>Registered Infrastructure Locations</h3>

      {assetsLoading ? (
        <p>Loading assets...</p>
      ) : assetError ? (
        <p>{assetError}</p>
      ) : assets.length === 0 ? (
        <p>No registered assets available.</p>
      ) : (
        assets.map((asset) => (
          <div
            key={asset.id}
            style={{
              padding: "16px",
              marginTop: "12px",
              border: "1px solid #e2e8f0",
              borderRadius: "8px"
            }}
          >
            <h4>{asset.name}</h4>
            <p>Asset ID: {asset.asset_code}</p>
            <p>Type: {asset.asset_type}</p>
            <p>Location: {asset.location}</p>
            <p>Department: {asset.department}</p>
          </div>
        ))
      )}
    </div>
  </section>
)}
{/* USER MANAGEMENT */}
{activePage === "User Management" && user?.role === "Admin" && (
  <section className="asset-module">
    <div className="asset-page-heading">
      <div>
        <span className="dashboard-eyebrow">
          ADMINISTRATION
        </span>
        <h1>User Management</h1>
        <p>View and manage registered InfraScan users.</p>
      </div>
    </div>

    <div className="ai-upload-card">
      <h3>Registered Users ({managedUsers.length})</h3>
      {usersSuccess && (
  <p style={{ color: "green" }}>{usersSuccess}</p>
)}

{usersError && (
  <p style={{ color: "red" }}>{usersError}</p>
)}

      <input
        type="text"
        placeholder="Search by name or email..."
        value={userSearch}
        onChange={(e) => setUserSearch(e.target.value)}
        style={{
          width: "100%",
          padding: "12px",
          marginTop: "14px",
          marginBottom: "16px",
          border: "1px solid #d1d5db",
          borderRadius: "8px",
        }}
      />

      {usersLoading ? (
        <p>Loading users...</p>
      ) : usersError ? (
        <p>{usersError}</p>
      ) : managedUsers.length === 0 ? (
        <p>No registered users found.</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{
            width: "100%",
            borderCollapse: "collapse",
            textAlign: "left",
          }}>
            <thead>
              <tr>
                <th style={{ padding: "12px" }}>ID</th>
                <th style={{ padding: "12px" }}>Full Name</th>
                <th style={{ padding: "12px" }}>Email</th>
                <th style={{ padding: "12px" }}>Role</th>
                <th style={{ padding: "12px" }}>Status</th>
                <th style={{ padding: "12px" }}>Created At</th>
                <th style={{ padding: "12px" }}>Action</th>
              </tr>
            </thead>

            <tbody>
              {managedUsers
                .filter((managedUser) =>
                  `${managedUser.full_name} ${managedUser.email}`
                    .toLowerCase()
                    .includes(userSearch.trim().toLowerCase())
                )
                .map((managedUser) => (
                  <tr key={managedUser.id}>
                    <td style={{ padding: "12px" }}>
                      {managedUser.id}
                    </td>
                    <td style={{ padding: "12px" }}>
                      {managedUser.full_name}
                    </td>
                    <td style={{ padding: "12px" }}>
                      {managedUser.email}
                    </td>
                    <td style={{ padding: "12px" }}>
                      {managedUser.role}
                    </td>
                    <td style={{ padding: "12px" }}>
                      {managedUser.is_active === 1
                        ? "Active"
                        : "Inactive"}
                    </td>
                    <td style={{ padding: "12px" }}>
                      {managedUser.created_at
                        ? new Date(
                            managedUser.created_at
                          ).toLocaleDateString()
                        : "—"}
                    </td>
                    <td style={{ padding: "12px" }}>
  {managedUser.id === user?.id ? (
    <span>Current Admin</span>
  ) : (
    <button
      onClick={() => handleUserStatusChange(managedUser)}
      style={{
        padding: "8px 12px",
        border: "none",
        borderRadius: "6px",
        cursor: "pointer",
        background:
          managedUser.is_active === 1
            ? "#fee2e2"
            : "#dcfce7",
        color:
          managedUser.is_active === 1
            ? "#b91c1c"
            : "#166534",
      }}
    >
      {managedUser.is_active === 1
        ? "Deactivate"
        : "Activate"}
    </button>
  )}
</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  </section>
)}

          {/* OTHER MODULES */}
          {activePage !== "Overview" &&
            activePage !== "Assets" &&
            activePage !== "Inspections" && 
            activePage !== "AI Damage Analysis" &&
            activePage !== "Damage Reports" && 
            activePage !== "Maintenance" && 
            activePage !== "Infrastructure Map" &&
            activePage !== "Historical Comparison" &&
            activePage !== "Damage Analytics" &&
            activePage !== "User Management" &&(
              <section className="module-placeholder">
                <div className="placeholder-icon">
                  {navigation.find(
                    (item) => item.name === activePage
                  )?.icon || "▦"}
                </div>

                <span className="dashboard-eyebrow">
                  INFRASCAN WORKSPACE
                </span>

                <h1>{activePage}</h1>

                <p>
                  This module is part of the InfraScan project workspace.
                  Its data and workflows will be connected as the
                  corresponding backend features are implemented.
                </p>

                <div className="module-info">
                  <strong>Module setup in progress</strong>
                  <span>Your signed-in account: {user.role}</span>
                </div>

                <button
                  className="return-button"
                  onClick={() => setActivePage("Overview")}
                >
                  ← Back to overview
                </button>
              </section>
            )}
        </div>
      </main>
    </div>
  );
}

export default App;
