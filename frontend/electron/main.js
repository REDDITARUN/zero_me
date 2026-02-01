const { app, BrowserWindow, globalShortcut, ipcMain, screen, session } = require('electron');
const path = require('path');

let dashboardWindow = null;
let blobWindow = null;

const isDev = process.env.NODE_ENV !== 'production' || !app.isPackaged;

function createDashboardWindow() {
  dashboardWindow = new BrowserWindow({
    width: 1000,
    height: 700,
    minWidth: 800,
    minHeight: 600,
    titleBarStyle: 'hiddenInset',
    trafficLightPosition: { x: 16, y: 16 },
    backgroundColor: '#faf9f7',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (isDev) {
    dashboardWindow.loadURL('http://localhost:5173');
    dashboardWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    dashboardWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  dashboardWindow.on('closed', () => {
    dashboardWindow = null;
  });
}

function createBlobWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;
  const blobSize = 120;

  blobWindow = new BrowserWindow({
    width: blobSize + 60,
    height: blobSize + 60,
    x: width - blobSize - 80,
    y: height - blobSize - 80,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    hasShadow: false,
    resizable: false,
    skipTaskbar: true,
    focusable: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Allow clicks to pass through transparent areas
  blobWindow.setIgnoreMouseEvents(false);

  // Keep blob visible on all desktops (macOS)
  blobWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

  if (isDev) {
    blobWindow.loadURL('http://localhost:5173/#/blob');
  } else {
    blobWindow.loadFile(path.join(__dirname, '../dist/index.html'), { hash: '/blob' });
  }

  blobWindow.on('closed', () => {
    blobWindow = null;
  });
}

function registerShortcuts() {
  // Cmd+Shift+S - Start
  globalShortcut.register('CommandOrControl+Shift+S', () => {
    if (dashboardWindow) {
      dashboardWindow.webContents.send('agent-control', 'start');
    }
    if (blobWindow) {
      blobWindow.webContents.send('agent-control', 'start');
    }
  });

  // Cmd+Shift+P - Pause
  globalShortcut.register('CommandOrControl+Shift+P', () => {
    if (dashboardWindow) {
      dashboardWindow.webContents.send('agent-control', 'pause');
    }
    if (blobWindow) {
      blobWindow.webContents.send('agent-control', 'pause');
    }
  });

  // Cmd+Shift+X - Stop
  globalShortcut.register('CommandOrControl+Shift+X', () => {
    if (dashboardWindow) {
      dashboardWindow.webContents.send('agent-control', 'stop');
    }
    if (blobWindow) {
      blobWindow.webContents.send('agent-control', 'stop');
    }
  });
}

// IPC handlers
ipcMain.on('show-blob', () => {
  if (!blobWindow) {
    createBlobWindow();
  } else {
    blobWindow.show();
  }
});

ipcMain.on('hide-blob', () => {
  if (blobWindow) {
    blobWindow.hide();
  }
});

ipcMain.on('minimize-dashboard', () => {
  if (dashboardWindow) {
    dashboardWindow.minimize();
  }
});

ipcMain.on('show-dashboard', () => {
  if (dashboardWindow) {
    dashboardWindow.show();
    dashboardWindow.focus();
  }
});

// Agent state sync between windows
ipcMain.on('agent-state', (event, state) => {
  if (dashboardWindow && !dashboardWindow.isDestroyed()) {
    dashboardWindow.webContents.send('agent-state', state);
  }
  if (blobWindow && !blobWindow.isDestroyed()) {
    blobWindow.webContents.send('agent-state', state);
  }
});

app.whenReady().then(() => {
  // Grant microphone permission for WebRTC
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    const allowedPermissions = ['media', 'mediaKeySystem', 'geolocation', 'notifications'];
    if (allowedPermissions.includes(permission)) {
      callback(true);
    } else {
      callback(false);
    }
  });

  // Also handle permission checks
  session.defaultSession.setPermissionCheckHandler((webContents, permission) => {
    const allowedPermissions = ['media', 'mediaKeySystem'];
    return allowedPermissions.includes(permission);
  });

  createDashboardWindow();
  registerShortcuts();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createDashboardWindow();
    }
  });
});

app.on('window-all-closed', () => {
  globalShortcut.unregisterAll();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});
