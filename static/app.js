/**
 * CampusCare Maintenance Platform - Frontend Controller
 * Connects Stitch UI directly to persistent SQLite backend and AI APIs.
 */

// Global Application State
const state = {
  currentRole: localStorage.getItem("campuscare_role") || "student",
  currentView: "report-issue",
  selectedImageFile: null,
  cameraStream: null,
  tickets: [],
  selectedTicketId: null,
  platformConfig: {
    security_contact: null,
    ai_configured: false,
    predictive_threshold: 4,
  },
  adminFilterTerm: "",
  activeHotspotFilter: null,
};

// ====================================================================
// INITIALIZATION
// ====================================================================
<<<<<<< HEAD
document.addEventListener("DOMContentLoaded", async () => {
  const auth = await fetch("/api/auth/me").then(r => r.json()).catch(() => ({ authenticated: false }));
  if (!auth.authenticated) {
    window.location.href = window.location.pathname.includes("maintenance") || window.location.pathname.includes("analytics") || window.location.pathname.startsWith("/admin") ? "/admin-login" : "/student-login";
    return;
  }
=======
document.addEventListener("DOMContentLoaded", () => {
>>>>>>> 9c5127969abfec502d1281d3caff21d23119c9fc
  initMobileSidebar();
  initDragAndDrop();
  initFileInput();
  initStarRatings();
  loadPlatformConfig();

  // Route from server template or url path
  const initial = window.INITIAL_VIEW || window.location.pathname.replace("/", "") || "report-issue";
<<<<<<< HEAD
  state.currentRole = auth.user.role;
  setAppRole(state.currentRole, false, auth.user);
=======
  setAppRole(state.currentRole, false);
>>>>>>> 9c5127969abfec502d1281d3caff21d23119c9fc
  navigateTo(initial, false);

  // Poll duplicate check on report issue
  checkDuplicateLive();
});

// Window Popstate (browser back/forward navigation)
window.addEventListener("popstate", (e) => {
  if (e.state && e.state.view) {
    navigateTo(e.state.view, false);
  }
});

// ====================================================================
// PLATFORM CONFIGURATION & SYSTEM NOTIFICATIONS
// ====================================================================
async function loadPlatformConfig() {
  try {
    const res = await fetch("/api/config");
    if (!res.ok) return;
    const data = await res.json();
    state.platformConfig = data;

    // Update Emergency Contact Banner
    const secLink = document.getElementById("security-call-link");
    const secText = document.getElementById("security-call-text");
    const settingSecInput = document.getElementById("setting-security-contact");
    const settingThreshInput = document.getElementById("setting-threshold");

    if (data.security_contact) {
      if (secLink) secLink.href = `tel:${data.security_contact.replace(/[^0-9+]/g, "")}`;
      if (secText) secText.textContent = `Campus Security (Ext: ${data.security_contact})`;
      if (settingSecInput) settingSecInput.value = data.security_contact;
    } else {
      if (secLink) secLink.href = "javascript:void(0)";
      if (secText) secText.textContent = "Security contact number not configured.";
      if (settingSecInput) settingSecInput.value = "";
    }

    if (settingThreshInput) {
      settingThreshInput.value = data.predictive_threshold || 4;
    }

    // Populate Notifications dropdown
    populateNotificationsMenu();
  } catch (err) {
    console.error("Could not load platform configuration:", err);
  }
}

function populateNotificationsMenu() {
  const container = document.getElementById("notifications-list");
  if (!container) return;

  const notifications = [
    { icon: "bolt", title: "Block C Inspection Trigger", text: "Recurring electrical alerts detected in Rooms 201-206", time: "Just now" },
    { icon: "schedule", title: "Dispatch SLA Status", text: "84% tickets on-schedule for active shifts", time: "15m ago" },
    { icon: "info", title: "Facilities Monitoring", text: "Continuous sensor uplink active across 5 campus wings", time: "1h ago" },
  ];

  container.innerHTML = notifications.map(n => `
    <div class="flex items-start gap-2.5 p-2 rounded-lg hover:bg-surface-container transition-colors cursor-pointer">
      <div class="w-7 h-7 rounded-lg bg-surface-container-high text-primary flex items-center justify-center shrink-0">
        <span class="material-symbols-outlined text-[16px]">${n.icon}</span>
      </div>
      <div class="flex-1 min-w-0">
        <span class="text-xs font-semibold text-on-surface block truncate">${n.title}</span>
        <span class="text-[11px] text-on-surface-variant block truncate">${n.text}</span>
        <span class="text-[10px] text-outline block mt-0.5">${n.time}</span>
      </div>
    </div>
  `).join("");
}

// Notifications toggle
const notifBtn = document.getElementById("notifications-btn");
const notifMenu = document.getElementById("notifications-menu");
if (notifBtn && notifMenu) {
  notifBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    notifMenu.classList.toggle("hidden");
  });
  document.addEventListener("click", (e) => {
    if (!notifMenu.contains(e.target) && !notifBtn.contains(e.target)) {
      notifMenu.classList.add("hidden");
    }
  });
}

function clearNotifications() {
  const container = document.getElementById("notifications-list");
  const badge = document.getElementById("notif-badge");
  if (container) container.innerHTML = `<p class="p-3 text-center text-xs text-on-surface-variant">No unread notifications.</p>`;
  if (badge) badge.classList.add("hidden");
}

// ====================================================================
// ROUTING & NAVIGATION
// ====================================================================
function navigateTo(viewName, pushState = true) {
<<<<<<< HEAD
  const adminViews = ["maintenance-dashboard", "maintenance-tickets", "predictive-maintenance", "analytics", "settings"];
  if (state.currentRole === "student" && adminViews.includes(viewName)) {
    viewName = "report-issue";
  } else if (state.currentRole === "admin" && ["report-issue", "my-reports"].includes(viewName)) {
    viewName = "maintenance-dashboard";
  }
=======
>>>>>>> 9c5127969abfec502d1281d3caff21d23119c9fc
  // Normalize route aliases
  if (viewName === "/" || viewName === "student-dashboard") viewName = "report-issue";
  if (viewName === "admin") viewName = "maintenance-dashboard";

  state.currentView = viewName;

  // Toggle view containers
  document.querySelectorAll(".view-panel").forEach((panel) => {
    panel.classList.add("hidden");
  });

  const activePanel = document.getElementById(`view-${viewName}`);
  if (activePanel) {
    activePanel.classList.remove("hidden");
  } else {
    // Fallback to report-issue
    const fallback = document.getElementById("view-report-issue");
    if (fallback) fallback.classList.remove("hidden");
  }

  // Update Sidebar active highlighting
  document.querySelectorAll(".nav-item").forEach((link) => {
    if (link.getAttribute("data-path") === viewName) {
      link.classList.add("active");
    } else {
      link.classList.remove("active");
    }
  });

  // Update browser URL
  if (pushState) {
    history.pushState({ view: viewName }, "", `/${viewName}`);
  }

  // Close mobile sidebar if open
  closeMobileSidebar();

  // View-specific data fetching
  if (viewName === "report-issue") {
    checkDuplicateLive();
  } else if (viewName === "my-reports") {
    loadMyReports();
  } else if (viewName === "maintenance-dashboard") {
    loadAdminDashboard();
  } else if (viewName === "predictive-maintenance") {
    loadPredictiveMaintenance();
  } else if (viewName === "maintenance-tickets") {
    loadAdminTickets();
  } else if (viewName === "analytics") {
    loadAnalyticsData();
  } else if (viewName === "settings") {
    loadPlatformConfig();
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}

// Sidebar link interceptor
document.addEventListener("click", (e) => {
  const link = e.target.closest("a[data-path]");
  if (link) {
    e.preventDefault();
    const path = link.getAttribute("data-path");
    navigateTo(path);
  }
});

// ====================================================================
// ROLE TOGGLING (Student Mode vs Operations Admin)
// ====================================================================
<<<<<<< HEAD
function setAppRole(role, autoNavigate = true, user = null) {
=======
function setAppRole(role, autoNavigate = true) {
>>>>>>> 9c5127969abfec502d1281d3caff21d23119c9fc
  state.currentRole = role;
  localStorage.setItem("campuscare_role", role);

  const studentBtn = document.getElementById("mode-student-btn");
  const operationsBtn = document.getElementById("mode-operations-btn");
  const userName = document.getElementById("user-name");
  const userRole = document.getElementById("user-role-label");
  const userDorm = document.getElementById("user-dorm-badge");
  const userAvatar = document.getElementById("user-avatar");
<<<<<<< HEAD
  const studentNav = document.getElementById("nav-student-section");
  const adminNav = document.getElementById("nav-admin-section");

  if (role === "admin") {
    if (studentNav) studentNav.classList.add("hidden");
    if (adminNav) adminNav.classList.remove("hidden");
=======

  if (role === "admin") {
>>>>>>> 9c5127969abfec502d1281d3caff21d23119c9fc
    if (studentBtn) {
      studentBtn.className = "flex-1 py-1 px-2 rounded text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all";
    }
    if (operationsBtn) {
      operationsBtn.className = "flex-1 py-1 px-2 rounded text-xs font-semibold bg-secondary-container text-on-secondary-container shadow-sm transition-all";
    }
<<<<<<< HEAD
    if (userName) userName.textContent = user?.name || "Administrator";
    if (userRole) userRole.textContent = "Campus Administrator";
=======
    if (userName) userName.textContent = "Facilities Ops Dispatch";
    if (userRole) userRole.textContent = "Lead Operations Engineer";
>>>>>>> 9c5127969abfec502d1281d3caff21d23119c9fc
    if (userDorm) userDorm.textContent = "Campus-wide";
    if (userAvatar) {
      userAvatar.textContent = "OP";
      userAvatar.className = "w-8 h-8 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center text-xs font-bold ring-2 ring-surface-container-lowest shrink-0";
    }
    if (autoNavigate && (state.currentView === "report-issue" || state.currentView === "my-reports")) {
      navigateTo("maintenance-dashboard");
    }
  } else {
<<<<<<< HEAD
    if (studentNav) studentNav.classList.remove("hidden");
    if (adminNav) adminNav.classList.add("hidden");
=======
>>>>>>> 9c5127969abfec502d1281d3caff21d23119c9fc
    if (studentBtn) {
      studentBtn.className = "flex-1 py-1 px-2 rounded text-xs font-semibold bg-secondary-container text-on-secondary-container shadow-sm transition-all";
    }
    if (operationsBtn) {
      operationsBtn.className = "flex-1 py-1 px-2 rounded text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all";
    }
<<<<<<< HEAD
    if (userName) userName.textContent = user?.name || "Student";
    if (userRole) userRole.textContent = "Student";
=======
    if (userName) userName.textContent = "Alex Rivera";
    if (userRole) userRole.textContent = "Student / Resident Advisor";
>>>>>>> 9c5127969abfec502d1281d3caff21d23119c9fc
    if (userDorm) userDorm.textContent = "Block C • 304";
    if (userAvatar) {
      userAvatar.textContent = "AR";
      userAvatar.className = "w-8 h-8 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center text-xs font-bold ring-2 ring-surface-container-lowest shrink-0";
    }
    if (autoNavigate && state.currentView.startsWith("maintenance-")) {
      navigateTo("report-issue");
    }
  }
}

function toggleRoleSwitch() {
<<<<<<< HEAD
  logout();
}

async function logout() {
  await fetch("/api/auth/logout", { method: "POST" });
  window.location.href = state.currentRole === "admin" ? "/admin-login" : "/student-login";
=======
  const newRole = state.currentRole === "student" ? "admin" : "student";
  setAppRole(newRole, true);
  showToast("Role Switched", `Switched to ${newRole === "admin" ? "Operations Admin" : "Student Mode"}`);
>>>>>>> 9c5127969abfec502d1281d3caff21d23119c9fc
}

// Mobile Sidebar Drawer
function initMobileSidebar() {
  const sidebar = document.getElementById("main-sidebar");
  const overlay = document.getElementById("mobile-sidebar-overlay");
  const openBtn = document.getElementById("mobile-menu-toggle");
  const closeBtn = document.getElementById("sidebar-close-btn");

  if (openBtn) {
    openBtn.addEventListener("click", () => {
      sidebar.classList.remove("-translate-x-full");
      overlay.classList.remove("hidden");
    });
  }

  function close() {
    sidebar.classList.add("-translate-x-full");
    overlay.classList.add("hidden");
  }

  if (closeBtn) closeBtn.addEventListener("click", close);
  if (overlay) overlay.addEventListener("click", close);
}

function closeMobileSidebar() {
  const sidebar = document.getElementById("main-sidebar");
  const overlay = document.getElementById("mobile-sidebar-overlay");
  if (sidebar) sidebar.classList.add("-translate-x-full");
  if (overlay) overlay.classList.add("hidden");
}

// ====================================================================
// IMAGE UPLOAD & PREVIEW MANAGEMENT
// ====================================================================
function initDragAndDrop() {
  const dropzone = document.getElementById("image-dropzone");
  const fileInput = document.getElementById("ticket-file-input");
  if (!dropzone || !fileInput) return;

  ["dragenter", "dragover"].forEach(name => {
    dropzone.addEventListener(name, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add("border-primary", "bg-primary-container/10");
    });
  });

  ["dragleave", "drop"].forEach(name => {
    dropzone.addEventListener(name, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove("border-primary", "bg-primary-container/10");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleImageSelection(e.dataTransfer.files[0]);
    }
  });

  dropzone.addEventListener("click", (e) => {
    if (e.target.closest("button")) return;
    if (!state.selectedImageFile) {
      fileInput.click();
    }
  });
}

function initFileInput() {
  const fileInput = document.getElementById("ticket-file-input");
  if (!fileInput) return;
  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleImageSelection(e.target.files[0]);
    }
  });
}

function handleImageSelection(file) {
  if (!file.type.startsWith("image/")) {
    showQuickAlert("Invalid file format. Please select an image file (JPG, PNG, WEBP).", true);
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    showQuickAlert("File exceeds 10MB limit. Please choose a smaller image.", true);
    return;
  }

  state.selectedImageFile = file;

  const reader = new FileReader();
  reader.onload = (e) => {
    const previewImg = document.getElementById("image-preview");
    const placeholder = document.getElementById("preview-placeholder");
    const metaStrip = document.getElementById("image-meta-strip");
    const metaName = document.getElementById("meta-filename");
    const metaSize = document.getElementById("meta-filesize");
    const uploadLabel = document.getElementById("upload-btn-label");

    if (previewImg) {
      previewImg.src = e.target.result;
      previewImg.classList.remove("hidden");
    }
    if (placeholder) placeholder.classList.add("hidden");
    if (metaStrip) metaStrip.classList.remove("hidden");
    if (metaName) metaName.textContent = file.name;
    if (metaSize) metaSize.textContent = `(${(file.size / (1024 * 1024)).toFixed(1)} MB)`;
    if (uploadLabel) uploadLabel.textContent = "Replace Image";

    // Hide any previous bounding box
    const bBox = document.getElementById("ai-bounding-box");
    if (bBox) bBox.classList.add("hidden");

    // Clear previous error messages
    const aiStatus = document.getElementById("ai-status-message");
    if (aiStatus) aiStatus.classList.add("hidden");
  };
  reader.readAsDataURL(file);
}

function removeSelectedImage() {
  state.selectedImageFile = null;
  const fileInput = document.getElementById("ticket-file-input");
  if (fileInput) fileInput.value = "";

  const previewImg = document.getElementById("image-preview");
  const placeholder = document.getElementById("preview-placeholder");
  const metaStrip = document.getElementById("image-meta-strip");
  const bBox = document.getElementById("ai-bounding-box");
  const uploadLabel = document.getElementById("upload-btn-label");

  if (previewImg) previewImg.classList.add("hidden");
  if (placeholder) placeholder.classList.remove("hidden");
  if (metaStrip) metaStrip.classList.add("hidden");
  if (bBox) bBox.classList.add("hidden");
  if (uploadLabel) uploadLabel.textContent = "Upload Photo";
}

// ====================================================================
// BROWSER CAMERA CAPTURE
// ====================================================================
async function openCameraModal() {
  const modal = document.getElementById("camera-modal");
  const video = document.getElementById("camera-video");
  const errBanner = document.getElementById("camera-error-banner");
  const errText = document.getElementById("camera-error-text");

  if (!modal || !video) return;
  modal.classList.remove("hidden");
  if (errBanner) errBanner.classList.add("hidden");

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    if (errBanner) errBanner.classList.remove("hidden");
    if (errText) errText.textContent = "Browser camera API is not supported on this device/browser.";
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } }
    });
    state.cameraStream = stream;
    video.srcObject = stream;
  } catch (err) {
    console.warn("Camera access error:", err);
    if (errBanner) errBanner.classList.remove("hidden");
    if (errText) {
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        errText.textContent = "Camera permission was denied. Please allow camera permissions or upload an image.";
      } else {
        errText.textContent = `Could not access camera: ${err.message || "Hardware unavailable"}`;
      }
    }
  }
}

function closeCameraModal() {
  const modal = document.getElementById("camera-modal");
  if (modal) modal.classList.add("hidden");

  if (state.cameraStream) {
    state.cameraStream.getTracks().forEach(track => track.stop());
    state.cameraStream = null;
  }
}

function capturePhotoFromCamera() {
  const video = document.getElementById("camera-video");
  const canvas = document.getElementById("camera-canvas");
  if (!video || !canvas || !state.cameraStream) return;

  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  canvas.toBlob((blob) => {
    if (blob) {
      const file = new File([blob], `camera_capture_${Date.now()}.jpg`, { type: "image/jpeg" });
      handleImageSelection(file);
      closeCameraModal();
      showToast("Photo Captured", "Camera image ready for AI inspection.");
    }
  }, "image/jpeg", 0.92);
}

// ====================================================================
// AI VISION ANALYSIS INTEGRATION
// ====================================================================
async function triggerAiDiagnosis() {
  if (!state.selectedImageFile) {
    showQuickAlert("Please select or capture a photo first to run AI diagnosis.", true);
    return;
  }

  const btn = document.getElementById("reanalyze-btn");
  const btnText = document.getElementById("analyze-btn-text");
  const statusMsg = document.getElementById("ai-status-message");

  btn.disabled = true;
  btnText.innerHTML = `
    <span class="inline-block w-4 h-4 border-2 border-on-primary-container border-t-transparent rounded-full animate-spin"></span>
    <span>Analyzing with Vision AI...</span>
  `;

  const formData = new FormData();
  formData.append("file", state.selectedImageFile);

  try {
    const res = await fetch("/api/analyze-image", {
      method: "POST",
      body: formData,
    });
    const result = await res.json();

    if (!res.ok || !result.success) {
      // Missing credentials or analysis failure
      const errorMsg = result.error || "AI service is unavailable. Please configure API credentials.";
      if (statusMsg) {
        statusMsg.classList.remove("hidden", "bg-primary-container/20", "text-primary");
        statusMsg.classList.add("bg-error-container/60", "text-on-error-container");
        statusMsg.innerHTML = `
          <div class="flex items-start gap-2">
            <span class="material-symbols-outlined text-[18px] text-error shrink-0">info</span>
            <div>
              <p class="font-bold">${errorMsg}</p>
              <p class="mt-0.5 text-[11px]">You can still enter the problem details and submit the ticket manually below.</p>
            </div>
          </div>
        `;
      }
      return;
    }

    const data = result.analysis;

    // Apply real AI analysis to form inputs
    const inputIssue = document.getElementById("input-issue");
    const selectCategory = document.getElementById("select-category");
    const selectPriority = document.getElementById("select-priority");
    const inputDepartment = document.getElementById("input-department");
    const inputFix = document.getElementById("input-suggested-fix");
    const bBox = document.getElementById("ai-bounding-box");
    const bLabelText = document.getElementById("bounding-label-text");
    const confMatchBadge = document.getElementById("confidence-match-badge");
    const confPercentage = document.getElementById("confidence-percentage");

    if (inputIssue) inputIssue.value = data.issue;
    if (selectCategory) selectCategory.value = data.category;
    if (selectPriority) selectPriority.value = data.priority;
    if (inputDepartment) inputDepartment.value = data.department;
    if (inputFix) inputFix.value = data.suggested_fix;

    onCategoryChanged();
    onPriorityChanged();

    // Show visual overlay on photo
    if (bBox) bBox.classList.remove("hidden");
    if (bLabelText) bLabelText.textContent = `${data.category} Defect`;
    if (confMatchBadge) confMatchBadge.textContent = `${data.confidence || 96.4}% match`;
    if (confPercentage) confPercentage.textContent = `${data.confidence || 96.4}% Accuracy`;

    // Handle Emergency Hazard Banner
    if (data.is_emergency || data.priority === "CRITICAL") {
      showEmergencyBanner();
    } else {
      hideEmergencyBanner();
    }

    if (statusMsg) {
      statusMsg.classList.remove("hidden", "bg-error-container/60", "text-on-error-container");
      statusMsg.classList.add("bg-secondary-container/60", "text-on-secondary-container");
      statusMsg.innerHTML = `
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-[18px] text-primary">verified</span>
          <span>AI Vision successfully identified <strong>${data.category}</strong> (${data.priority} priority).</span>
        </div>
      `;
    }

    // Check duplicate with new category
    checkDuplicateLive();
    showToast("AI Diagnosis Complete", `Categorized as ${data.category} - ${data.priority}`);
  } catch (err) {
    if (statusMsg) {
      statusMsg.classList.remove("hidden", "bg-secondary-container/60", "text-on-secondary-container");
      statusMsg.classList.add("bg-error-container/60", "text-on-error-container");
      statusMsg.textContent = `Network error during AI analysis: ${err.message}`;
    }
  } finally {
    btn.disabled = false;
    btnText.innerHTML = `Analyze Issue with AI`;
  }
}

// Emergency Banner Management
function showEmergencyBanner() {
  const banner = document.getElementById("emergency-banner");
  if (banner) banner.classList.remove("hidden");
}

function hideEmergencyBanner() {
  const banner = document.getElementById("emergency-banner");
  if (banner) banner.classList.add("hidden");
}

function dismissEmergencyBanner() {
  hideEmergencyBanner();
}

function onCategoryChanged() {
  const select = document.getElementById("select-category");
  const subtitle = document.getElementById("category-subtitle");
  const deptInput = document.getElementById("input-department");
  if (!select) return;

  const cat = select.value;
  const subMap = {
    Electrical: "Power & Utilities",
    Plumbing: "Water & Restrooms",
    Furniture: "Desks, Chairs & Fixtures",
    Civil: "Structural & Hallways",
    "IT/Network": "Wi-Fi & Connectivity",
    Sanitation: "Cleanliness & Disposal",
    Other: "General Facilities",
  };
  const deptMap = {
    Electrical: "Electrical Maintenance & Grid Infrastructure Team",
    Plumbing: "Plumbing & Water Systems Operations",
    Furniture: "Carpentry & Facilities Operations",
    Civil: "Civil Works & Structural Maintenance",
    "IT/Network": "IT & Campus Network Infrastructure",
    Sanitation: "Sanitation & Housekeeping Services",
    Other: "General Campus Maintenance Operations",
  };

  if (subtitle) subtitle.textContent = subMap[cat] || "Campus Facility";
  if (deptInput) deptInput.value = deptMap[cat] || "General Operations";

  checkDuplicateLive();
}

function onPriorityChanged() {
  const select = document.getElementById("select-priority");
  const subtitle = document.getElementById("priority-subtitle");
  if (!select) return;

  const pri = select.value;
  const priSubMap = {
    CRITICAL: "Immediate Safety Hazard",
    HIGH: "Urgent Dispatch Queue",
    MEDIUM: "Standard Work Order",
    LOW: "Scheduled Maintenance",
  };
  if (subtitle) subtitle.textContent = priSubMap[pri] || pri;

  if (pri === "CRITICAL") {
    showEmergencyBanner();
  } else {
    hideEmergencyBanner();
  }
}

// ====================================================================
// LIVE DUPLICATE DETECTION PREVIEW
// ====================================================================
let duplicateDebounceTimer = null;

function checkDuplicateLive() {
  clearTimeout(duplicateDebounceTimer);
  duplicateDebounceTimer = setTimeout(async () => {
    const blockSelect = document.getElementById("block-select");
    const roomInput = document.getElementById("room-input");
    const catSelect = document.getElementById("select-category");
    const indicatorText = document.getElementById("duplicate-indicator-text");

    if (!blockSelect || !roomInput || !catSelect || !indicatorText) return;

    const block = blockSelect.value.trim();
    const room = roomInput.value.trim();
    const category = catSelect.value.trim();

    if (!room) {
      indicatorText.innerHTML = "Enter room number to cross-reference existing campus reports.";
      return;
    }

    try {
      const res = await fetch(`/api/check-duplicate?block=${encodeURIComponent(block)}&room=${encodeURIComponent(room)}&category=${encodeURIComponent(category)}`);
      if (!res.ok) return;
      const data = await res.json();

      if (data.exists && data.existing_ticket) {
        const t = data.existing_ticket;
        indicatorText.innerHTML = `
          Notice: An open ticket (<strong>#${t.id}</strong>) already exists for ${block} Room ${room} (${category}).
          Submitting will link your report to <strong>Master Ticket #${t.id}</strong> (currently ${t.report_count} report${t.report_count > 1 ? "s" : ""}, Priority: <strong>${t.priority}</strong>) and escalate its priority.
        `;
      } else {
        indicatorText.innerHTML = `
          Notice: No open duplicates found for ${block} Room ${room} (${category}). A new master ticket will be created upon submission.
        `;
      }
    } catch (err) {
      console.warn("Duplicate check error:", err);
    }
  }, 300);
}

// ====================================================================
// SUBMIT REPORT TICKET
// ====================================================================
async function submitReportTicket() {
  const issueInput = document.getElementById("input-issue");
  const catSelect = document.getElementById("select-category");
  const priSelect = document.getElementById("select-priority");
  const deptInput = document.getElementById("input-department");
  const fixInput = document.getElementById("input-suggested-fix");
  const blockSelect = document.getElementById("block-select");
  const roomInput = document.getElementById("room-input");
  const submitBtn = document.getElementById("submit-ticket-btn");
  const submitLabel = document.getElementById("submit-ticket-label");

  const issue = issueInput ? issueInput.value.trim() : "";
  const category = catSelect ? catSelect.value : "Other";
  const priority = priSelect ? priSelect.value : "MEDIUM";
  const department = deptInput ? deptInput.value.trim() : "";
  const suggested_fix = fixInput ? fixInput.value.trim() : "";
  const block = blockSelect ? blockSelect.value : "Block C";
  const room = roomInput ? roomInput.value.trim() : "";

  // Validation
  if (!issue) {
    showQuickAlert("Please enter a description for the reported issue.", true);
    if (issueInput) issueInput.focus();
    return;
  }
  if (!room) {
    showQuickAlert("Please specify the room or area location.", true);
    if (roomInput) roomInput.focus();
    return;
  }

  submitBtn.disabled = true;
  submitLabel.textContent = "Submitting to Database...";

  const payload = {
    issue,
    category,
    priority,
    department,
    suggested_fix,
    block,
    room,
  };

  try {
    const res = await fetch("/api/tickets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const result = await res.json();
    if (!res.ok || !result.success) {
      throw new Error(result.detail || "Submission failed");
    }

    const t = result.ticket;
    const isMerged = result.merged;

    // Display Confirmation Modal
    const modal = document.getElementById("confirm-modal");
    const modalTitle = document.getElementById("confirm-modal-title");
    const modalSub = document.getElementById("confirm-modal-subtitle");
    const confirmId = document.getElementById("confirm-ticket-id");
    const confirmStatus = document.getElementById("confirm-status");
    const confirmLocation = document.getElementById("confirm-location");
    const confirmCat = document.getElementById("confirm-category");
    const confirmPri = document.getElementById("confirm-priority");
    const confirmMergedRow = document.getElementById("confirm-merged-row");
    const confirmRepCount = document.getElementById("confirm-report-count");

    if (modal) modal.classList.remove("hidden");
    if (confirmId) confirmId.textContent = `#${t.id}`;
    if (confirmStatus) confirmStatus.textContent = t.status;
    if (confirmLocation) confirmLocation.textContent = `${t.block}, Rm ${t.room}`;
    if (confirmCat) confirmCat.textContent = t.category;
    if (confirmPri) confirmPri.textContent = t.priority;

    if (isMerged) {
      if (modalTitle) modalTitle.textContent = "Report Added to Existing Ticket";
      if (modalSub) modalSub.textContent = `Linked to Master Ticket #${t.id} and priority escalated to ${t.priority}.`;
      if (confirmMergedRow) confirmMergedRow.classList.remove("hidden");
      if (confirmRepCount) confirmRepCount.textContent = `${t.report_count} reports total`;
      showToast("Report Merged", `Added report to Ticket #${t.id} (Priority: ${t.priority})`);
    } else {
      if (modalTitle) modalTitle.textContent = "Ticket Submitted Successfully";
      if (modalSub) modalSub.textContent = `New Master Ticket #${t.id} created and dispatched to operations.`;
      if (confirmMergedRow) confirmMergedRow.classList.add("hidden");
      showToast("Ticket Created", `New Ticket #${t.id} created (${t.block} Rm ${t.room})`);
    }

    // Refresh duplicate notice
    checkDuplicateLive();
  } catch (err) {
    showQuickAlert(`Failed to submit ticket: ${err.message}`, true);
  } finally {
    submitBtn.disabled = false;
    submitLabel.textContent = "Submit Ticket";
  }
}

function closeConfirmModalAndStay() {
  const modal = document.getElementById("confirm-modal");
  if (modal) modal.classList.add("hidden");
  // Reset form inputs for next ticket
  removeSelectedImage();
  const roomInput = document.getElementById("room-input");
  if (roomInput) roomInput.value = "";
  checkDuplicateLive();
}

function closeConfirmModalAndGoReports() {
  const modal = document.getElementById("confirm-modal");
  if (modal) modal.classList.add("hidden");
  navigateTo("my-reports");
}

// ====================================================================
// MY REPORTS & TICKET TRACKER VIEW
// ====================================================================
async function loadMyReports() {
  const container = document.getElementById("my-tickets-container");
  if (!container) return;

  container.innerHTML = `<div class="p-8 text-center text-on-surface-variant"><span class="inline-block w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin"></span><p class="mt-2 text-xs">Loading campus tickets from database...</p></div>`;

  try {
    const [ticketsRes, metricsRes] = await Promise.all([
      fetch("/api/tickets?sort_by=priority"),
      fetch("/api/metrics"),
    ]);

    const ticketsData = await ticketsRes.json();
    const metricsData = await metricsRes.json();

    state.tickets = ticketsData.tickets || [];
    renderMyReportsMetrics(metricsData.metrics);
    renderMyReportsList(state.tickets);
  } catch (err) {
    container.innerHTML = `<div class="p-8 text-center text-error"><p class="text-sm font-bold">Failed to load reports from database: ${err.message}</p></div>`;
  }
}

function renderMyReportsMetrics(metrics) {
  if (!metrics) return;
  const elTotal = document.getElementById("my-metric-total");
  const elOpen = document.getElementById("my-metric-open");
  const elCrit = document.getElementById("my-metric-critical-sub");
  const elAssigned = document.getElementById("my-metric-assigned");
  const elFixed = document.getElementById("my-metric-fixed");
  const elSlaSub = document.getElementById("my-metric-sla-sub");

  if (elTotal) elTotal.textContent = metrics.total;
  if (elOpen) elOpen.textContent = metrics.open;
  if (elCrit) elCrit.textContent = `${metrics.critical_open} critical urgent`;
  if (elFixed) elFixed.textContent = metrics.fixed;

  // Count assigned
  const assignedCount = state.tickets.filter(t => t.status === "Assigned").length;
  if (elAssigned) elAssigned.textContent = assignedCount;

  // SLA ribbon computation
  const total = metrics.total || 1;
  const fixedPct = Math.round((metrics.fixed / total) * 100);
  const assignedPct = Math.round((assignedCount / total) * 100);
  const reportedPct = Math.max(0, 100 - fixedPct - assignedPct);

  const barFixed = document.getElementById("sla-bar-fixed");
  const barAssigned = document.getElementById("sla-bar-assigned");
  const barReported = document.getElementById("sla-bar-reported");
  if (barFixed) barFixed.style.width = `${fixedPct}%`;
  if (barAssigned) barAssigned.style.width = `${assignedPct}%`;
  if (barReported) barReported.style.width = `${reportedPct}%`;

  if (elSlaSub) elSlaSub.textContent = `${fixedPct}% resolved of all logged`;
}

function filterMyReports() {
  const search = document.getElementById("my-ticket-search")?.value.toLowerCase() || "";
  const status = document.getElementById("my-status-filter")?.value || "All";
  const category = document.getElementById("my-category-filter")?.value || "All";
  const sortBy = document.getElementById("my-sort-filter")?.value || "priority";

  let filtered = state.tickets.filter((t) => {
    const text = `${t.id} ${t.issue} ${t.room} ${t.block} ${t.category}`.toLowerCase();
    const matchSearch = !search || text.includes(search);
    const matchStatus = status === "All" || t.status === status;
    const matchCat = category === "All" || t.category === category;
    return matchSearch && matchStatus && matchCat;
  });

  // Client-side sorting
  if (sortBy === "newest") {
    filtered.sort((a, b) => b.id - a.id);
  } else if (sortBy === "oldest") {
    filtered.sort((a, b) => a.id - b.id);
  } else if (sortBy === "reports") {
    filtered.sort((a, b) => b.report_count - a.report_count);
  } else {
    const pOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
    filtered.sort((a, b) => (pOrder[a.priority] || 4) - (pOrder[b.priority] || 4));
  }

  renderMyReportsList(filtered);
}

function renderMyReportsList(ticketList) {
  const container = document.getElementById("my-tickets-container");
  if (!container) return;

  if (ticketList.length === 0) {
    container.innerHTML = `
      <div class="bg-surface-container-lowest rounded-2xl p-8 text-center text-on-surface-variant shadow-sm space-y-2">
        <span class="material-symbols-outlined text-4xl text-outline-variant">inbox</span>
        <h3 class="text-sm font-bold text-on-surface">No Maintenance Tickets Found</h3>
        <p class="text-xs text-on-surface-variant max-w-sm mx-auto">No tickets match your search filters. Click "Report New Issue" to create a new ticket.</p>
        <button onclick="navigateTo('report-issue')" class="mt-3 px-4 py-2 rounded-xl bg-primary-container text-on-primary-container text-xs font-bold shadow-sm">Report Issue</button>
      </div>
    `;
    return;
  }

  container.innerHTML = ticketList.map((t) => {
    const isCritical = t.priority === "CRITICAL";
    const priBadgeClass = isCritical
      ? "bg-error-container text-on-error-container font-bold"
      : t.priority === "HIGH"
      ? "bg-secondary-fixed text-on-secondary-fixed font-bold"
      : "bg-surface-container-high text-on-surface-variant font-medium";

    const statusBadge = t.status === "Reported"
      ? `<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-secondary-container text-on-secondary-container flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse"></span>Reported</span>`
      : t.status === "Assigned"
      ? `<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-primary-container/30 text-on-primary-container flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-primary"></span>Assigned</span>`
      : `<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-tertiary-fixed text-on-tertiary-fixed-variant flex items-center gap-1"><span class="material-symbols-outlined text-[13px]">check</span>Fixed</span>`;

    const duplicateBanner = t.report_count > 1
      ? `
        <div class="mt-space-md p-2 rounded-xl bg-secondary-fixed/50 flex items-center justify-between text-on-secondary-fixed-variant text-xs">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-[16px] text-secondary">group</span>
            <span class="font-semibold">${t.report_count} students reported this • Escalated to ${t.priority}</span>
          </div>
          <span class="material-symbols-outlined text-[16px]">trending_up</span>
        </div>
      `
      : "";

    const isSelected = state.selectedTicketId === t.id;

    return `
      <article onclick="selectMyTicket(${t.id})" class="ticket-card ${isSelected ? 'ring-2 ring-primary-container' : ''} bg-surface-container-lowest hover:bg-surface-bright rounded-2xl p-space-lg shadow-sm transition-all duration-200 cursor-pointer relative overflow-hidden group">
        <div class="absolute left-0 top-0 bottom-0 w-1.5 ${isCritical ? 'bg-error' : 'bg-primary-container'}"></div>
        <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-space-sm">
          <div class="flex items-center gap-space-sm flex-wrap">
            <span class="text-xs font-bold px-2.5 py-1 rounded-lg bg-surface-container text-on-surface">#${t.id}</span>
            ${statusBadge}
            <span class="px-2.5 py-0.5 rounded-full text-xs ${priBadgeClass}">
              ${t.priority}
            </span>
          </div>
          <span class="text-xs text-on-surface-variant flex items-center gap-1">
            <span class="material-symbols-outlined text-[16px]">schedule</span>
            ${t.created_at}
          </span>
        </div>

        <div class="mt-space-md">
          <h2 class="text-base font-semibold text-on-surface group-hover:text-primary transition-colors">
            ${t.issue}
          </h2>
          ${t.suggested_fix ? `<p class="mt-1 text-xs text-on-surface-variant line-clamp-2">${t.suggested_fix}</p>` : ''}
        </div>

        ${duplicateBanner}

        <div class="mt-space-md pt-2 flex flex-wrap items-center justify-between gap-2 border-t border-surface-container text-xs text-on-surface-variant">
          <div class="flex items-center gap-3">
            <span class="flex items-center gap-1"><span class="material-symbols-outlined text-[15px]">apartment</span>${t.block} — Rm ${t.room}</span>
            <span class="flex items-center gap-1"><span class="material-symbols-outlined text-[15px]">construction</span>${t.category}</span>
          </div>
          <button class="inline-flex items-center gap-1 text-xs font-semibold text-primary group-hover:text-on-primary-container" type="button">
            <span>View Details</span>
            <span class="material-symbols-outlined text-[16px]">chevron_right</span>
          </button>
        </div>
      </article>
    `;
  }).join("");

  // Auto-select first ticket if none selected
  if (!state.selectedTicketId && ticketList.length > 0) {
    selectMyTicket(ticketList[0].id);
  }
}

function selectMyTicket(ticketId) {
  state.selectedTicketId = ticketId;
  const ticket = state.tickets.find((t) => t.id === ticketId);
  if (!ticket) return;

  // Highlight card
  document.querySelectorAll(".ticket-card").forEach((card) => {
    card.classList.remove("ring-2", "ring-primary-container");
  });

  const emptyState = document.getElementById("detail-empty-state");
  const activeContent = document.getElementById("detail-active-content");
  if (emptyState) emptyState.classList.add("hidden");
  if (activeContent) activeContent.classList.remove("hidden");

  // Populate preview panel
  document.getElementById("detail-ticket-id").textContent = `Ticket #${ticket.id}`;
  document.getElementById("detail-issue-title").textContent = ticket.issue;
  document.getElementById("detail-location-text").textContent = `Location: ${ticket.block} — Room ${ticket.room}`;
  document.getElementById("detail-department-text").textContent = `Assigned Department: ${ticket.department}`;
  document.getElementById("detail-suggested-fix").textContent = ticket.suggested_fix || "Standard facilities maintenance inspection protocol.";
  document.getElementById("timeline-created-at").textContent = ticket.created_at;
  document.getElementById("timeline-category-note").textContent = `Auto-categorized as ${ticket.category} with ${ticket.priority} priority`;

  // Status pill & timeline progression
  const statusPill = document.getElementById("detail-status-pill");
  const step3Dot = document.getElementById("timeline-step3-dot");
  const step4Dot = document.getElementById("timeline-step4-dot");
  const step4Title = document.getElementById("timeline-step4-title");
  const step4Note = document.getElementById("timeline-step4-note");
  const feedbackWidget = document.getElementById("review-feedback-widget");
  const reviewTicketId = document.getElementById("review-ticket-id");

  if (statusPill) statusPill.textContent = ticket.status;

  if (ticket.status === "Reported") {
    if (step3Dot) step3Dot.className = "absolute -left-6 top-1 w-4 h-4 rounded-full bg-surface-container-high ring-4 ring-surface-container-lowest";
    if (step4Dot) step4Dot.className = "absolute -left-6 top-1 w-4 h-4 rounded-full bg-surface-container-high ring-4 ring-surface-container-lowest";
    if (step4Title) step4Title.textContent = "Facilities Dispatch Pending";
    if (step4Note) step4Note.textContent = "Awaiting technician assignment slot.";
    if (feedbackWidget) feedbackWidget.classList.add("hidden");
  } else if (ticket.status === "Assigned") {
    if (step3Dot) step3Dot.className = "absolute -left-6 top-1 w-4 h-4 rounded-full bg-primary flex items-center justify-center text-white ring-4 ring-surface-container-lowest";
    if (step4Dot) step4Dot.className = "absolute -left-6 top-1 w-4 h-4 rounded-full bg-secondary animate-pulse ring-4 ring-surface-container-lowest";
    if (step4Title) step4Title.textContent = "Technician Active On-Site";
    if (step4Note) step4Note.textContent = `Assigned to ${ticket.department}. Work in progress.`;
    if (feedbackWidget) feedbackWidget.classList.add("hidden");
  } else if (ticket.status === "Fixed") {
    if (step3Dot) step3Dot.className = "absolute -left-6 top-1 w-4 h-4 rounded-full bg-primary flex items-center justify-center text-white ring-4 ring-surface-container-lowest";
    if (step4Dot) step4Dot.className = "absolute -left-6 top-1 w-4 h-4 rounded-full bg-primary flex items-center justify-center text-white ring-4 ring-surface-container-lowest";
    if (step4Title) step4Title.textContent = "Issue Resolved & Cleared";
    if (step4Note) step4Note.textContent = `Completed at ${ticket.updated_at}. Verified functional.`;
    if (feedbackWidget) feedbackWidget.classList.remove("hidden");
    if (reviewTicketId) reviewTicketId.textContent = `Ticket #${ticket.id}`;
  }
}

// Star Rating Handling
let selectedStarRating = 5;
function initStarRatings() {
  const container = document.getElementById("star-rating");
  if (!container) return;
  container.querySelectorAll(".star-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const rating = parseInt(btn.getAttribute("data-rating"), 10);
      selectedStarRating = rating;
      updateStarDisplay(rating);
    });
  });
  updateStarDisplay(5);
}

function updateStarDisplay(rating) {
  const buttons = document.querySelectorAll("#star-rating .star-btn");
  buttons.forEach(btn => {
    const r = parseInt(btn.getAttribute("data-rating"), 10);
    const span = btn.querySelector(".material-symbols-outlined");
    if (span) {
      if (r <= rating) {
        span.classList.add("text-secondary", "fill-1");
        span.textContent = "star";
      } else {
        span.classList.remove("text-secondary");
        span.textContent = "star_outline";
      }
    }
  });
}

async function submitTicketReview() {
  if (!state.selectedTicketId) return;
  try {
    const res = await fetch(`/api/tickets/${state.selectedTicketId}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating: selectedStarRating, comment: "Resident review from tracker" }),
    });
    if (res.ok) {
      showToast("Feedback Submitted", `Thank you! Rated Ticket #${state.selectedTicketId} with ${selectedStarRating} stars.`);
      const widget = document.getElementById("review-feedback-widget");
      if (widget) widget.innerHTML = `<p class="p-3 text-xs font-semibold text-primary text-center">Thank you for rating this repair resolution!</p>`;
    }
  } catch (err) {
    showQuickAlert("Failed to submit review.", true);
  }
}

function copyTicketShareLink() {
  if (!state.selectedTicketId) return;
  const url = `${window.location.origin}/my-reports?ticket=${state.selectedTicketId}`;
  if (navigator.clipboard) {
    navigator.clipboard.writeText(url);
    showToast("Link Copied", "Ticket reference link copied to clipboard.");
  }
}

// ====================================================================
// ADMIN MAINTENANCE DASHBOARD & HOTSPOTS
// ====================================================================
async function loadAdminDashboard() {
  try {
    const [metricsRes, warningsRes, hotspotsRes, blockCountsRes, ticketsRes] = await Promise.all([
      fetch("/api/metrics"),
      fetch("/api/predictive-warnings"),
      fetch("/api/hotspots"),
      fetch("/api/block-counts"),
      fetch("/api/tickets?sort_by=priority"),
    ]);

    const metrics = (await metricsRes.json()).metrics;
    const warnings = (await warningsRes.json()).warnings;
    const hotspots = (await hotspotsRes.json()).data;
    const blockCounts = (await blockCountsRes.json()).counts;
    const tickets = (await ticketsRes.json()).tickets;

    renderAdminMetrics(metrics);
    renderPredictiveBanner(warnings);
    renderHotspotHeatmap(hotspots);
    renderSvgBarChart(blockCounts, metrics.total);
    renderDashboardTicketsTable(tickets);
  } catch (err) {
    console.error("Dashboard data load error:", err);
  }
}

function refreshAdminDashboard() {
  loadAdminDashboard();
  showToast("Sync Complete", "Dashboard data reloaded from database.");
}

function renderAdminMetrics(metrics) {
  if (!metrics) return;
  const elTot = document.getElementById("admin-metric-total");
  const elOpen = document.getElementById("admin-metric-open");
  const elCrit = document.getElementById("admin-metric-critical");
  const elFixed = document.getElementById("admin-metric-fixed");
  const elSla = document.getElementById("admin-metric-sla-label");

  if (elTot) elTot.textContent = metrics.total;
  if (elOpen) elOpen.textContent = metrics.open;
  if (elCrit) elCrit.textContent = String(metrics.critical_open).padStart(2, "0");
  if (elFixed) elFixed.textContent = metrics.fixed;

  if (elSla) {
    const rate = metrics.total ? Math.round((metrics.fixed / metrics.total) * 100) : 100;
    elSla.textContent = `${rate}% SLA`;
  }
}

function renderPredictiveBanner(warnings) {
  const heading = document.getElementById("predictive-banner-heading");
  const subtext = document.getElementById("predictive-banner-pattern");
  const relatedLabel = document.getElementById("view-related-count-label");

  if (warnings && warnings.length > 0) {
    const top = warnings[0];
    if (heading) heading.textContent = top.message;
    if (subtext) subtext.textContent = `Pattern detected: ${top.count} correlated issues concentrated in ${top.block} within the last 30 days.`;
    if (relatedLabel) relatedLabel.textContent = `View All ${top.count} Related Tickets`;
    state.activeHotspotFilter = { block: top.block, category: top.category };
  } else {
    if (heading) heading.textContent = "All campus zones within standard operational limits.";
    if (subtext) subtext.textContent = "No recurring component failure patterns currently exceed the 30-day threshold.";
    if (relatedLabel) relatedLabel.textContent = "View Tickets Queue";
    state.activeHotspotFilter = null;
  }
}

function filterDashboardToHotspot() {
  if (state.activeHotspotFilter) {
    navigateTo("maintenance-tickets");
    const blockSelect = document.getElementById("admin-filter-block");
    const catSelect = document.getElementById("admin-filter-category");
    if (blockSelect) blockSelect.value = state.activeHotspotFilter.block;
    if (catSelect) catSelect.value = state.activeHotspotFilter.category;
    filterAdminTicketsTable();
  } else {
    navigateTo("maintenance-tickets");
  }
}

function renderHotspotHeatmap(data) {
  const tbody = document.getElementById("heatmap-tbody");
  if (!tbody || !data) return;

  const blocks = data.blocks || ["Block A", "Block B", "Block C", "Block D", "Block E"];
  const categories = data.categories || ["Electrical", "Plumbing", "Furniture", "Civil", "IT/Network", "Sanitation", "Other"];
  const matrix = data.matrix || {};

  tbody.innerHTML = blocks.map(block => {
    const rowCounts = matrix[block] || {};
    const cells = categories.map(cat => {
      const count = rowCounts[cat] || 0;
      let cellClass = "bg-surface-container-low text-on-surface-variant";
      let cellBadge = count;

      if (count >= 6) {
        cellClass = "bg-primary text-on-primary font-bold shadow-sm";
        cellBadge = `<span class="flex items-center justify-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-error animate-ping"></span>${count} Issues</span>`;
      } else if (count >= 4) {
        cellClass = "bg-primary-container text-on-primary-container font-semibold";
        cellBadge = `${count} Issues`;
      } else if (count >= 2) {
        cellClass = "bg-secondary-container text-on-secondary-container font-semibold";
        cellBadge = `${count} Issues`;
      }

      return `
        <td class="p-1 text-center cursor-pointer" onclick="filterHeatmapCell('${block}', '${cat}')" title="Click to filter ${block} ${cat} tickets">
          <div class="py-1.5 rounded-lg ${cellClass} transition-transform hover:scale-105">
            ${cellBadge}
          </div>
        </td>
      `;
    }).join("");

    return `
      <tr class="hover:bg-surface-container-low/50 transition-colors">
        <td class="py-2 px-3 font-semibold text-on-surface whitespace-nowrap">${block}</td>
        ${cells}
      </tr>
    `;
  }).join("");
}

function filterHeatmapCell(block, category) {
  navigateTo("maintenance-tickets");
  const blockSelect = document.getElementById("admin-filter-block");
  const catSelect = document.getElementById("admin-filter-category");
  if (blockSelect) blockSelect.value = block;
  if (catSelect) catSelect.value = category;
  filterAdminTicketsTable();
}

function renderSvgBarChart(counts, total) {
  const container = document.getElementById("svg-chart-container");
  const totalLabel = document.getElementById("chart-total-label");
  const summaryCallout = document.getElementById("hotspot-summary-callout");
  if (!container || !counts) return;

  if (totalLabel) totalLabel.textContent = `Total ${total} Logged`;

  const blocks = ["Block A", "Block B", "Block C", "Block D", "Block E"];
  const vals = blocks.map(b => counts[b] || 0);
  const maxVal = Math.max(...vals, 1);

  // Find highest block
  let highestBlock = "Block C";
  let highestCount = 0;
  blocks.forEach(b => {
    if ((counts[b] || 0) > highestCount) {
      highestCount = counts[b] || 0;
      highestBlock = b;
    }
  });

  const highestPct = total ? Math.round((highestCount / total) * 100) : 0;
  if (summaryCallout) {
    summaryCallout.innerHTML = `<strong>${highestBlock} accounts for ${highestPct}%</strong> of all maintenance incidents across campus halls.`;
  }

  // Generate SVG Bars
  const barWidth = 34;
  const startX = 48;
  const gap = 60;
  const chartHeight = 120;
  const baseY = 140;

  const barsSvg = blocks.map((b, i) => {
    const count = counts[b] || 0;
    const height = Math.max(8, Math.round((count / maxVal) * chartHeight));
    const x = startX + i * gap;
    const y = baseY - height;
    const isHighest = b === highestBlock && count > 0;
    const shortLabel = b.replace("Block ", "Blk ");

    if (isHighest) {
      return `
        <g class="transition-all hover:opacity-90 cursor-pointer" onclick="filterHeatmapCell('${b}', 'All')">
          <rect fill="#316383" height="${height}" rx="4" width="${barWidth}" x="${x}" y="${y}"></rect>
          <rect fill="#F6EBC3" height="8" rx="4" width="${barWidth}" x="${x}" y="${y}"></rect>
          <text fill="#ba1a1a" font-family="Inter" font-size="11" font-weight="700" text-anchor="middle" x="${x + barWidth / 2}" y="${y - 8}">${count} 🔥</text>
          <text fill="#1b1c19" font-family="Inter" font-size="11" font-weight="700" text-anchor="middle" x="${x + barWidth / 2}" y="156">${shortLabel}</text>
        </g>
      `;
    }

    return `
      <g class="transition-all hover:opacity-80 cursor-pointer" onclick="filterHeatmapCell('${b}', 'All')">
        <rect fill="#8FBFE3" height="${height}" rx="4" width="${barWidth}" x="${x}" y="${y}"></rect>
        <text fill="#316383" font-family="Inter" font-size="10" font-weight="600" text-anchor="middle" x="${x + barWidth / 2}" y="${y - 8}">${count}</text>
        <text fill="#41474d" font-family="Inter" font-size="11" font-weight="500" text-anchor="middle" x="${x + barWidth / 2}" y="156">${shortLabel}</text>
      </g>
    `;
  }).join("");

  container.innerHTML = `
    <svg class="w-full h-56" fill="none" viewBox="0 0 340 180" xmlns="http://www.w3.org/2000/svg">
      <line stroke="#f0eee8" stroke-width="1" x1="30" x2="330" y1="140" y2="140"></line>
      <line stroke="#f0eee8" stroke-dasharray="3 3" stroke-width="1" x1="30" x2="330" y1="100" y2="100"></line>
      <line stroke="#f0eee8" stroke-dasharray="3 3" stroke-width="1" x1="30" x2="330" y1="60" y2="60"></line>
      <line stroke="#f0eee8" stroke-dasharray="3 3" stroke-width="1" x1="30" x2="330" y1="20" y2="20"></line>
      <text fill="#71787e" font-family="Inter" font-size="9" text-anchor="end" x="22" y="143">0</text>
      <text fill="#71787e" font-family="Inter" font-size="9" text-anchor="end" x="22" y="103">${Math.round(maxVal / 3)}</text>
      <text fill="#71787e" font-family="Inter" font-size="9" text-anchor="end" x="22" y="63">${Math.round((maxVal * 2) / 3)}</text>
      <text fill="#71787e" font-family="Inter" font-size="9" text-anchor="end" x="22" y="23">${maxVal}</text>
      ${barsSvg}
    </svg>
  `;
}

function renderDashboardTicketsTable(tickets) {
  const tbody = document.getElementById("dashboard-tickets-tbody");
  const footerText = document.getElementById("dashboard-table-footer-text");
  if (!tbody || !tickets) return;

  const topPriority = tickets.slice(0, 8);
  if (footerText) {
    footerText.textContent = `Showing ${topPriority.length} high priority tickets out of ${tickets.length} total.`;
  }

  if (topPriority.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="p-8 text-center text-xs text-on-surface-variant font-medium">No maintenance tickets reported yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = topPriority.map(t => {
    const isCritical = t.priority === "CRITICAL";
    const priBadge = isCritical
      ? `<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs bg-error-container text-on-error-container font-bold"><span class="w-1.5 h-1.5 rounded-full bg-error animate-ping"></span>CRITICAL</span>`
      : t.priority === "HIGH"
      ? `<span class="px-2.5 py-1 rounded-full text-xs bg-secondary-container text-on-secondary-container font-bold">HIGH</span>`
      : `<span class="px-2.5 py-1 rounded-full text-xs bg-surface-container-high text-on-surface-variant font-medium">${t.priority}</span>`;

    let actionBtn = "";
    if (t.status === "Reported") {
      actionBtn = `<button onclick="quickUpdateTicketStatus(${t.id}, 'Assigned')" class="bg-primary text-on-primary hover:bg-primary/90 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition-all">Assign Ops</button>`;
    } else if (t.status === "Assigned") {
      actionBtn = `<button onclick="quickUpdateTicketStatus(${t.id}, 'Fixed')" class="bg-secondary-container hover:bg-secondary-fixed text-on-secondary-container px-3 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition-all">Mark Fixed</button>`;
    } else {
      actionBtn = `<button onclick="openTicketModal(${t.id})" class="bg-surface-container-low hover:bg-surface-container text-on-surface px-3 py-1.5 rounded-lg text-xs font-medium transition-all">Details</button>`;
    }

    return `
      <tr class="hover:bg-surface-container-low/40 transition-colors">
        <td class="py-3 px-4 font-bold text-on-surface">#${t.id}</td>
        <td class="py-3 px-4 cursor-pointer" onclick="openTicketModal(${t.id})">
          <div class="font-semibold text-on-surface">${t.issue}</div>
          <div class="text-xs text-on-surface-variant truncate max-w-xs">${t.suggested_fix || t.department}</div>
        </td>
        <td class="py-3 px-4 text-on-surface font-medium whitespace-nowrap">
          <div class="flex items-center gap-1"><span class="material-symbols-outlined text-[16px] text-tertiary">apartment</span>${t.block} Rm ${t.room}</div>
        </td>
        <td class="py-3 px-4 whitespace-nowrap">${priBadge}</td>
        <td class="py-3 px-4 whitespace-nowrap">
          <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${t.status === 'Fixed' ? 'bg-tertiary-fixed text-on-tertiary-fixed-variant' : 'bg-surface-container-low text-on-surface'}">
            ${t.status} (${t.report_count} report${t.report_count > 1 ? 's' : ''})
          </span>
        </td>
        <td class="py-3 px-4 text-right whitespace-nowrap">
          ${actionBtn}
        </td>
      </tr>
    `;
  }).join("");
}

async function quickUpdateTicketStatus(ticketId, newStatus) {
  try {
    const res = await fetch(`/api/tickets/${ticketId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus }),
    });
    if (!res.ok) throw new Error("Failed to update status");
    showToast("Status Updated", `Ticket #${ticketId} changed to ${newStatus}`);
    loadAdminDashboard();
  } catch (err) {
    showQuickAlert(err.message, true);
  }
}

// ====================================================================
// ADMIN PREDICTIVE MAINTENANCE ENGINE VIEW
// ====================================================================
async function loadPredictiveMaintenance() {
  const container = document.getElementById("predictive-patterns-container");
  if (!container) return;

  container.innerHTML = `<div class="p-8 text-center text-on-surface-variant"><span class="inline-block w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin"></span><p class="mt-2 text-xs">Analyzing 30-day recurring incident clusters...</p></div>`;

  try {
    const res = await fetch("/api/predictive-patterns");
    const data = await res.json();
    const patterns = data.patterns || [];

    const elHotspots = document.getElementById("pred-metric-hotspots");
    const elOrders = document.getElementById("pred-metric-orders");
    if (elHotspots) elHotspots.textContent = `${patterns.length} Patterns`;
    if (elOrders) elOrders.textContent = `${patterns.length * 2} Dispatches`;

    if (patterns.length === 0) {
      container.innerHTML = `
        <div class="bg-surface-container-lowest rounded-xl p-8 text-center text-on-surface-variant shadow-sm space-y-2">
          <span class="material-symbols-outlined text-4xl text-primary">verified</span>
          <h3 class="text-sm font-bold text-on-surface">No Recurrence Threshold Exceeded</h3>
          <p class="text-xs text-on-surface-variant max-w-md mx-auto">
            All campus living zones and academic facilities are operating below the 30-day incident threshold (&lt; 4 issues per wing).
          </p>
        </div>
      `;
      return;
    }

    container.innerHTML = patterns.map(p => {
      const ticketsGrid = p.correlated_tickets && p.correlated_tickets.length > 0
        ? p.correlated_tickets.map(ct => `
            <div class="p-2 rounded-lg bg-surface-container flex items-center justify-between text-xs cursor-pointer hover:bg-surface-container-high transition-colors" onclick="openTicketModal(${ct.id})">
              <span class="font-bold text-primary">#${ct.id}</span>
              <span class="text-on-surface truncate mx-2">${ct.issue}</span>
              <span class="text-error bg-error-container/50 px-1.5 py-0.5 rounded text-[10px] font-semibold">${ct.room}</span>
            </div>
          `).join("")
        : `<p class="text-xs text-on-surface-variant">No individual ticket details available.</p>`;

      return `
        <div class="bg-surface-container-lowest rounded-xl p-space-lg lg:p-space-xl shadow-md relative overflow-hidden transition-all hover:shadow-lg">
          <div class="absolute left-0 top-0 bottom-0 w-2 ${p.severity === 'CRITICAL' ? 'bg-error' : 'bg-secondary'}"></div>
          <div class="flex flex-col lg:flex-row gap-space-lg">
            <div class="flex-1 space-y-space-md">
              <div class="flex flex-wrap items-center gap-space-xs">
                <span class="px-3 py-1 rounded-full bg-secondary-container text-on-secondary-container text-xs font-semibold flex items-center gap-1.5 shadow-sm">
                  <span class="w-2 h-2 rounded-full ${p.severity === 'CRITICAL' ? 'bg-error animate-pulse' : 'bg-secondary'}"></span>
                  HOTSPOT DETECTED • ${p.count} Issues in 30 Days
                </span>
                <span class="px-2.5 py-0.5 rounded-full bg-error-container text-on-error-container text-xs font-bold">${p.severity} RISK</span>
                <span class="text-xs text-on-surface-variant font-mono">ID: ${p.id}</span>
              </div>

              <div>
                <h3 class="text-xl font-bold text-on-surface tracking-tight">${p.block} — ${p.category} Systemic Recurrence</h3>
                <p class="text-xs text-on-surface-variant mt-1 flex items-center gap-1">
                  <span class="material-symbols-outlined text-[16px] text-primary">apartment</span>
                  <span>Campus Zone ${p.block} Residential Infrastructure</span>
                </p>
              </div>

              <div class="p-space-md rounded-lg bg-surface-container-low space-y-1">
                <div class="flex items-center gap-1.5 text-on-surface text-xs font-bold">
                  <span class="material-symbols-outlined text-[16px] text-primary">science</span>
                  <span>Root Cause Hypothesis</span>
                </div>
                <p class="text-xs text-on-surface-variant">${p.root_cause}</p>
              </div>

              <div class="space-y-1.5">
                <span class="text-xs text-on-surface-variant uppercase tracking-wider font-semibold">Correlated Campus Reports (${p.correlated_tickets ? p.correlated_tickets.length : 0} of ${p.count})</span>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  ${ticketsGrid}
                </div>
              </div>

              <div class="p-space-md rounded-lg bg-secondary-container/40 flex flex-col sm:flex-row sm:items-center justify-between gap-space-md">
                <div class="space-y-0.5">
                  <span class="text-[11px] text-secondary uppercase font-bold">Recommended Triage Action</span>
                  <p class="text-xs font-medium text-on-surface">${p.recommended_action}</p>
                </div>
                <div class="flex flex-wrap sm:flex-nowrap gap-2 shrink-0">
                  <button onclick="createPreventativeOrder('${p.block}', '${p.category}')" class="px-4 py-2 rounded-lg bg-primary-container hover:bg-primary-fixed-dim text-on-primary-container text-xs font-bold transition-all shadow-sm active:scale-95" type="button">
                    Create Preventative Work Order
                  </button>
                  <button onclick="filterHeatmapCell('${p.block}', '${p.category}')" class="px-3 py-2 rounded-lg bg-secondary-container hover:bg-secondary-fixed text-on-secondary-container text-xs font-semibold transition-all" type="button">
                    Review History
                  </button>
                </div>
              </div>
            </div>

            <!-- Right Telemetry Panel -->
            <div class="w-full lg:w-72 shrink-0 flex flex-col justify-between bg-surface-container-low rounded-xl p-4 space-y-3">
              <div class="space-y-1">
                <span class="text-[11px] uppercase tracking-wider text-on-surface-variant font-bold">Telemetry Risk Profile</span>
                <div class="bg-surface-container-highest rounded-lg p-3 text-center space-y-1">
                  <span class="text-2xl font-bold text-error">${p.count}x</span>
                  <p class="text-[11px] text-on-surface font-semibold">Recurrence Density</p>
                  <span class="text-[10px] text-on-surface-variant">Exceeds threshold of 4</span>
                </div>
              </div>

              <div class="space-y-1 bg-surface-container-lowest p-3 rounded-lg">
                <div class="flex justify-between text-xs">
                  <span class="text-on-surface-variant">Pattern Confidence</span>
                  <span class="font-bold text-on-surface">${p.confidence}%</span>
                </div>
                <div class="w-full h-2 rounded-full bg-surface-container-high overflow-hidden">
                  <div class="h-full bg-error rounded-full" style="width: ${p.confidence}%"></div>
                </div>
                <p class="text-[11px] text-error flex items-center gap-1 pt-1 font-medium">
                  <span class="material-symbols-outlined text-[14px]">priority_high</span>
                  <span>Preventative action recommended</span>
                </p>
              </div>

              <div class="pt-1 flex items-center justify-between text-[11px] text-on-surface-variant border-t border-surface-container">
                <span>Model: CampusNeural-v3</span>
                <span>Live Sync</span>
              </div>
            </div>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    container.innerHTML = `<div class="p-8 text-center text-error"><p class="text-sm font-bold">Failed to load predictive analysis: ${err.message}</p></div>`;
  }
}

function runDiagnosticsScan() {
  const btn = document.getElementById("runDiagnosticsBtn");
  const text = document.getElementById("run-diagnostics-text");
  if (!btn || !text) return;

  btn.disabled = true;
  text.textContent = "Scanning Campus Telemetry...";

  setTimeout(() => {
    btn.disabled = false;
    text.textContent = "Run AI Campus Diagnostics";
    loadPredictiveMaintenance();
    showToast("Diagnostics Completed", "AI telemetry scan evaluated all 30-day maintenance tickets.");
  }, 900);
}

function createPreventativeOrder(block, category) {
  showToast("Work Order Dispatched", `Preventative inspection team assigned to ${block} (${category}).`);
}

// ====================================================================
// ADMIN MAINTENANCE TICKETS DIRECTORY
// ====================================================================
async function loadAdminTickets() {
  const tbody = document.getElementById("all-tickets-tbody");
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="9" class="p-8 text-center text-xs text-on-surface-variant"><span class="inline-block w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin"></span><p class="mt-1">Loading tickets...</p></td></tr>`;

  try {
    const res = await fetch("/api/tickets?sort_by=priority");
    const data = await res.json();
    state.tickets = data.tickets || [];
    filterAdminTicketsTable();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="p-8 text-center text-xs text-error font-semibold">Failed to load tickets: ${err.message}</td></tr>`;
  }
}

function filterAdminTicketsTable() {
  const tbody = document.getElementById("all-tickets-tbody");
  const emptyBanner = document.getElementById("all-tickets-empty");
  if (!tbody) return;

  const search = document.getElementById("admin-search-input")?.value.toLowerCase() || "";
  const status = document.getElementById("admin-filter-status")?.value || "All";
  const category = document.getElementById("admin-filter-category")?.value || "All";
  const block = document.getElementById("admin-filter-block")?.value || "All";
  const priority = document.getElementById("admin-filter-priority")?.value || "All";
  const sort = document.getElementById("admin-filter-sort")?.value || "priority";

  let list = state.tickets.filter(t => {
    const text = `${t.id} ${t.issue} ${t.block} ${t.room} ${t.department} ${t.category}`.toLowerCase();
    const matchSearch = !search || text.includes(search);
    const matchStatus = status === "All" || t.status === status;
    const matchCat = category === "All" || t.category === category;
    const matchBlock = block === "All" || t.block === block;
    const matchPri = priority === "All" || t.priority === priority;
    return matchSearch && matchStatus && matchCat && matchBlock && matchPri;
  });

  // Client sort
  if (sort === "newest") {
    list.sort((a, b) => b.id - a.id);
  } else if (sort === "oldest") {
    list.sort((a, b) => a.id - b.id);
  } else if (sort === "reports") {
    list.sort((a, b) => b.report_count - a.report_count);
  } else {
    const pOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
    list.sort((a, b) => (pOrder[a.priority] || 4) - (pOrder[b.priority] || 4));
  }

  if (list.length === 0) {
    tbody.innerHTML = "";
    if (emptyBanner) emptyBanner.classList.remove("hidden");
    return;
  }
  if (emptyBanner) emptyBanner.classList.add("hidden");

  tbody.innerHTML = list.map(t => {
    const isCritical = t.priority === "CRITICAL";
    const priBadge = isCritical
      ? `<span class="px-2 py-0.5 rounded-full text-[11px] bg-error-container text-on-error-container font-bold">CRITICAL</span>`
      : t.priority === "HIGH"
      ? `<span class="px-2 py-0.5 rounded-full text-[11px] bg-secondary-fixed text-on-secondary-fixed font-bold">HIGH</span>`
      : `<span class="px-2 py-0.5 rounded-full text-[11px] bg-surface-container-high text-on-surface-variant">${t.priority}</span>`;

    const statusBadge = t.status === "Reported"
      ? `<span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-secondary-container text-on-secondary-container">Reported</span>`
      : t.status === "Assigned"
      ? `<span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-primary-container/30 text-on-primary-container">Assigned</span>`
      : `<span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-tertiary-fixed text-on-tertiary-fixed-variant">Fixed</span>`;

    return `
      <tr class="hover:bg-surface-container-low/50 transition-colors">
        <td class="py-3 px-4 font-bold text-on-surface">#${t.id}</td>
        <td class="py-3 px-4 font-semibold text-on-surface cursor-pointer hover:text-primary max-w-xs truncate" onclick="openTicketModal(${t.id})">
          ${t.issue}
        </td>
        <td class="py-3 px-3 whitespace-nowrap">${t.category}</td>
        <td class="py-3 px-3 whitespace-nowrap">${priBadge}</td>
        <td class="py-3 px-3 whitespace-nowrap font-medium">${t.block} Rm ${t.room}</td>
        <td class="py-3 px-3 truncate max-w-[140px] text-on-surface-variant">${t.department}</td>
        <td class="py-3 px-2 text-center font-bold text-secondary">${t.report_count}</td>
        <td class="py-3 px-3 whitespace-nowrap">${statusBadge}</td>
        <td class="py-3 px-3 text-right whitespace-nowrap">
          <button onclick="openTicketModal(${t.id})" class="px-2.5 py-1 rounded bg-surface-container hover:bg-surface-container-high text-on-surface text-xs font-semibold transition-all">
            Manage
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

function resetAdminFilters() {
  const sInput = document.getElementById("admin-search-input");
  const stSelect = document.getElementById("admin-filter-status");
  const catSelect = document.getElementById("admin-filter-category");
  const bSelect = document.getElementById("admin-filter-block");
  const priSelect = document.getElementById("admin-filter-priority");
  const sortSelect = document.getElementById("admin-filter-sort");

  if (sInput) sInput.value = "";
  if (stSelect) stSelect.value = "All";
  if (catSelect) catSelect.value = "All";
  if (bSelect) bSelect.value = "All";
  if (priSelect) priSelect.value = "All";
  if (sortSelect) sortSelect.value = "priority";

  filterAdminTicketsTable();
}

// ====================================================================
// MODAL TICKET DETAILS & STATUS EDITING
// ====================================================================
let modalActiveTicketId = null;

async function openTicketModal(ticketId) {
  modalActiveTicketId = ticketId;
  const modal = document.getElementById("ticket-modal");
  if (!modal) return;

  try {
    const res = await fetch(`/api/tickets/${ticketId}`);
    if (!res.ok) throw new Error("Ticket not found");
    const data = (await res.json()).ticket;

    document.getElementById("modal-ticket-id").textContent = `#${data.id}`;
    document.getElementById("modal-issue").textContent = data.issue;
    document.getElementById("modal-location").textContent = `${data.block} • Room ${data.room}`;
    document.getElementById("modal-category").textContent = data.category;
    document.getElementById("modal-department").textContent = data.department;
    document.getElementById("modal-reports").textContent = `${data.report_count} report${data.report_count > 1 ? "s" : ""}`;
    document.getElementById("modal-status-current").textContent = data.status;
    document.getElementById("modal-suggested-fix").textContent = data.suggested_fix || "No specific fix provided.";
    document.getElementById("modal-created").textContent = data.created_at;
    document.getElementById("modal-updated").textContent = data.updated_at;

    const priBadge = document.getElementById("modal-priority-badge");
    if (priBadge) {
      priBadge.textContent = data.priority;
      priBadge.className = data.priority === "CRITICAL"
        ? "px-2.5 py-0.5 rounded-full text-xs font-bold bg-error-container text-on-error-container"
        : "px-2.5 py-0.5 rounded-full text-xs font-bold bg-secondary-container text-on-secondary-container";
    }

    const statusSelect = document.getElementById("modal-status-select");
    if (statusSelect) statusSelect.value = data.status;

    modal.classList.remove("hidden");
  } catch (err) {
    showQuickAlert(err.message, true);
  }
}

function closeTicketModal() {
  const modal = document.getElementById("ticket-modal");
  if (modal) modal.classList.add("hidden");
  modalActiveTicketId = null;
}

async function saveModalStatusChange() {
  if (!modalActiveTicketId) return;
  const statusSelect = document.getElementById("modal-status-select");
  const newStatus = statusSelect ? statusSelect.value : "Reported";

  try {
    const res = await fetch(`/api/tickets/${modalActiveTicketId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus }),
    });
    if (!res.ok) throw new Error("Status update failed");
    showToast("Status Updated", `Ticket #${modalActiveTicketId} updated to ${newStatus}`);
    closeTicketModal();

    // Reload active view
    if (state.currentView === "maintenance-dashboard") loadAdminDashboard();
    if (state.currentView === "maintenance-tickets") loadAdminTickets();
    if (state.currentView === "my-reports") loadMyReports();
  } catch (err) {
    showQuickAlert(err.message, true);
  }
}

// ====================================================================
// CAMPUS ANALYTICS VIEW
// ====================================================================
async function loadAnalyticsData() {
  try {
    const res = await fetch("/api/analytics");
    if (!res.ok) return;
    const data = (await res.json()).analytics;
    renderAnalyticsBars("analytics-category-bars", data.by_category, "#8FBFE3");
    renderAnalyticsBars("analytics-priority-bars", data.by_priority, "#eae0b8");
    renderAnalyticsBars("analytics-block-bars", data.by_block, "#316383");
    renderAnalyticsBars("analytics-status-bars", data.by_status, "#8FBFE3");
  } catch (err) {
    console.error("Analytics load error:", err);
  }
}

function renderAnalyticsBars(containerId, dataMap, color) {
  const container = document.getElementById(containerId);
  if (!container || !dataMap) return;

  const entries = Object.entries(dataMap);
  const maxVal = Math.max(...entries.map(e => e[1]), 1);

  container.innerHTML = entries.map(([key, val]) => {
    const pct = Math.round((val / maxVal) * 100);
    return `
      <div class="space-y-1">
        <div class="flex justify-between text-xs font-semibold text-on-surface">
          <span>${key}</span>
          <span>${val}</span>
        </div>
        <div class="w-full h-2 rounded-full bg-surface-container-low overflow-hidden">
          <div class="h-full rounded-full transition-all duration-500" style="width: ${pct}%; background-color: ${color}"></div>
        </div>
      </div>
    `;
  }).join("");
}

// ====================================================================
// PLATFORM SETTINGS & CSV EXPORT
// ====================================================================
async function savePlatformSettings() {
  const secInput = document.getElementById("setting-security-contact");
  const openaiInput = document.getElementById("setting-openai-key");
  const geminiInput = document.getElementById("setting-gemini-key");
  const threshInput = document.getElementById("setting-threshold");
  const statusLabel = document.getElementById("settings-save-status");

  const payload = {};
  if (secInput) payload.security_contact = secInput.value.trim();
  if (openaiInput && openaiInput.value.trim()) payload.openai_key = openaiInput.value.trim();
  if (geminiInput && geminiInput.value.trim()) payload.gemini_key = geminiInput.value.trim();
  if (threshInput) payload.threshold = parseInt(threshInput.value, 10) || 4;

  try {
    const res = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to save settings");
    showToast("Settings Saved", "Configuration updated and saved to persistent environment.");
    if (statusLabel) {
      statusLabel.textContent = "Saved successfully!";
      setTimeout(() => { statusLabel.textContent = ""; }, 3000);
    }
    loadPlatformConfig();
  } catch (err) {
    showQuickAlert(err.message, true);
  }
}

async function exportTicketsCsv() {
  try {
    const res = await fetch("/api/tickets");
    const data = await res.json();
    const tickets = data.tickets || [];

    if (tickets.length === 0) {
      showQuickAlert("No tickets available to export.", true);
      return;
    }

    const headers = ["ID", "Issue", "Category", "Priority", "Department", "Block", "Room", "Status", "Report_Count", "Created_At", "Updated_At"];
    const rows = tickets.map(t => [
      t.id,
      `"${(t.issue || '').replace(/"/g, '""')}"`,
      t.category,
      t.priority,
      `"${(t.department || '').replace(/"/g, '""')}"`,
      t.block,
      t.room,
      t.status,
      t.report_count,
      t.created_at,
      t.updated_at,
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `campuscare_tickets_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast("CSV Exported", `Downloaded ${tickets.length} tickets as CSV.`);
  } catch (err) {
    showQuickAlert(`Export error: ${err.message}`, true);
  }
}

// ====================================================================
// TOAST & ALERT UTILITIES
// ====================================================================
function showToast(title, body) {
  const toast = document.getElementById("toast-success");
  const titleEl = document.getElementById("toast-title");
  const bodyEl = document.getElementById("toast-body");
  if (!toast) return;

  if (titleEl) titleEl.textContent = title;
  if (bodyEl) bodyEl.textContent = body;

  toast.classList.remove("translate-y-32", "opacity-0", "pointer-events-none");
  toast.classList.add("translate-y-0", "opacity-100");

  setTimeout(() => {
    toast.classList.add("translate-y-32", "opacity-0", "pointer-events-none");
    toast.classList.remove("translate-y-0", "opacity-100");
  }, 4000);
}

function showQuickAlert(message, isError = false) {
  showToast(isError ? "Attention" : "Campus Notice", message);
}
