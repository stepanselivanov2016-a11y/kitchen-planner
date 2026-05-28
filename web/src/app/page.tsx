"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type CountertopMaterial =
  | "chipboard_plastic"
  | "quartz_agglomerate"
  | "natural_stone"
  | "acrylic_stone"
  | "compact_plate";

type CustomerHeightMode =
  | "height_170_or_below"
  | "exact"
  | "height_196_or_above";
type CeilingType = "stretch" | "plasterboard";

type SizeAdjustment = {
  field: "sink.width_mm" | "dishwasher.width_mm" | string;
  label: string;
  from_mm?: number;
  to_mm?: number;
  from_value?: string;
  to_value?: string;
  reason: string;
};

type KitchenOptions = {
  room: {
    layout_shape: "straight" | "corner";
    wall_length_mm: number;
    side_1_width_mm: number;
    side_2_width_mm: number;
    kitchen_height_mm: number;
    wall_cabinets_enabled: boolean;
    mezzanine_enabled: boolean;
    upper_cabinet_opening: "hinged" | "lift";
    ceiling_type: CeilingType;
    entry_side: "left" | "right";
    customer_height_mode: CustomerHeightMode;
    customer_height_cm: number;
    countertop_material: CountertopMaterial;
    countertop_thickness_mm: number;
  };
  required: {
    refrigerator: {
      mode: "built_in" | "freestanding";
      freestanding_installation: "in_cabinet" | "solo";
      width_mm: number;
      depth_mm: number;
      height_mm: number;
      gap_mm: number;
    };
    oven: {
      placement: "under_counter" | "column";
    };
    sink: {
      width_mm: number;
    };
    hood: {
      type: "built_in" | "solo";
      width_mm: number;
    };
    microwave: {
      type: "built_in" | "upper_built_in" | "solo";
      width_mm: number;
      height_mm: number;
    };
    hob: {
      cabinet_width_mm: number;
    };
  };
  optional: {
    dishwasher: {
      enabled: boolean;
      width_mm: number;
    };
    undercounter_fridge: {
      enabled: boolean;
    };
  };
  locked: Record<string, boolean>;
};

type Result = {
  normalized_spec: Record<string, unknown>;
  module_options: KitchenOptions;
  generated_layout: {
    sink_edge?: "left" | "right";
    fridge_edge?: "left" | "right";
    customer_height_mode?: CustomerHeightMode;
    customer_height_cm?: number;
    countertop_height_mm?: number;
    kitchen_height_mm?: number;
    wall_cabinets_enabled?: boolean;
    mezzanine_enabled?: boolean;
    base_module_height_mm?: number;
    plinth_height_mm?: number;
    countertop_material?: CountertopMaterial;
    countertop_material_label?: string;
    countertop_thickness_mm?: number;
    size_adjustments?: SizeAdjustment[];
    modules: Array<Record<string, unknown>>;
    wall_modules: Array<Record<string, unknown>>;
    front_objects: Array<Record<string, unknown>>;
    warnings: string[];
  };
  top_view_svg: string;
  front_view_svg: string;
  side_view_svg?: string;
};

type PlanError = {
  error?: string;
  detail?: string;
};

type SavedGeneration = {
  id: number | string;
  createdAt: string;
  title: string;
  shape: "straight" | "corner";
  widthLabel: string;
  autoFields: string[];
  lockedFields: string[];
  adjustmentCount: number;
  details?: GenerationDetails;
};

type LocalUser = {
  login: string;
  history: SavedGeneration[];
};

type ApiGeneration = {
  id: number;
  created_at: string;
  title: string;
  shape: "straight" | "corner";
  width_label: string;
  auto_fields: string[];
  locked_fields: string[];
  adjustment_count: number;
  details?: GenerationDetails;
};

type GenerationDetails = {
  module_options?: KitchenOptions;
  result?: Result;
  size_adjustments?: SizeAdjustment[];
  warnings?: string[];
};

type ApiProfile = {
  login: string;
  history: ApiGeneration[];
};

type AuthResponse = {
  access_token: string;
  token_type: string;
  user: {
    login: string;
  };
};

type PreferenceParseResponse = {
  patch: Record<string, string | number | boolean>;
  locked: string[];
  notes: string[];
  source: "ollama" | "rules" | "hybrid" | "empty";
};

const SESSION_STORAGE_KEY = "kitchen_planner_access_token";

const hoodPresetWidths = [600, 900, 1200, 1800];
const AUTO_SELECT_VALUE = "__auto__";

const countertopMaterialLabels: Record<CountertopMaterial, string> = {
  chipboard_plastic: "ДСП пластик",
  quartz_agglomerate: "Кварцевый агломерат",
  natural_stone: "Натуральный камень",
  acrylic_stone: "Искусственный камень (акрил)",
  compact_plate: "Компакт-плита",
};

const countertopThicknessOptions: Record<CountertopMaterial, number[]> = {
  chipboard_plastic: [28, 38],
  quartz_agglomerate: [20, 40, 60],
  natural_stone: [20, 50],
  acrylic_stone: [20, 30, 40, 51],
  compact_plate: [12],
};

function lockKeyFromPreferenceField(field: string) {
  return field
    .replace(/^required\./, "")
    .replace(/^optional\./, "")
    .replace(/^room\./, "room.");
}

function manualPreferencePhrase(field: string, patch: Record<string, unknown>) {
  const value = Object.values(patch)[0];

  switch (field) {
    case "room.layout_shape":
      return value === "corner" ? "Кухня угловая." : "Кухня прямая.";
    case "room.wall_cabinets_enabled":
      return value ? "Нужны навесные шкафы." : "Без навесных шкафов.";
    case "room.mezzanine_enabled":
      return value ? "Нужны антресольные шкафы." : "Без антресольных шкафов.";
    case "room.upper_cabinet_opening":
      return value === "lift"
        ? "Верхние шкафы с подъёмными фасадами."
        : "Верхние шкафы распашные.";
    case "room.ceiling_type":
      return value === "stretch" ? "Потолок натяжной." : "Потолок гипсокартонный.";
    case "room.entry_side":
      return value === "left" ? "Вывод воды слева." : "Вывод воды справа.";
    case "refrigerator.mode":
      return value === "built_in" ? "Холодильник встроенный." : "Холодильник отдельностоящий.";
    case "refrigerator.freestanding_installation":
      return value === "solo"
        ? "Отдельностоящий холодильник рядом с кухней."
        : "Отдельностоящий холодильник в мебельном каркасе.";
    case "oven.placement":
      return value === "column" ? "Духовка в колонне." : "Духовка под столешницей.";
    case "sink.width_mm":
      return `Мойка ${value} мм.`;
    case "hood.type":
      return value === "built_in" ? "Вытяжка встроенная." : "Вытяжка соло.";
    case "hood.width_mm":
      return `Вытяжка ${value} мм.`;
    case "microwave.type":
      if (value === "upper_built_in") {
        return "СВЧ встроенная в верхний шкаф.";
      }
      return value === "built_in" ? "СВЧ встроенная в колонну." : "СВЧ соло.";
    case "microwave.width_mm":
      return `СВЧ шириной ${value} мм.`;
    case "microwave.height_mm":
      return `СВЧ высотой ${value} мм.`;
    case "hob.cabinet_width_mm":
      return `Варочная ${value} мм.`;
    case "dishwasher.width_mm":
      return `Посудомоечная машина ${value} мм.`;
    case "undercounter_fridge.enabled":
      return value ? "Нужен подстольный холодильник." : "Без подстольного холодильника.";
    default:
      return "";
  }
}

const countertopCustomThicknessDefaults: Partial<
  Record<CountertopMaterial, number>
> = {
  quartz_agglomerate: 30,
  acrylic_stone: 35,
};

function materialAllowsCustomThickness(material: CountertopMaterial) {
  return material === "quartz_agglomerate" || material === "acrylic_stone";
}

const defaultOptions: KitchenOptions = {
  room: {
    layout_shape: "straight",
    wall_length_mm: 3000,
    side_1_width_mm: 3000,
    side_2_width_mm: 2400,
    kitchen_height_mm: 2700,
    wall_cabinets_enabled: true,
    mezzanine_enabled: true,
    upper_cabinet_opening: "hinged",
    ceiling_type: "stretch",
    entry_side: "left",
    customer_height_mode: "exact",
    customer_height_cm: 175,
    countertop_material: "chipboard_plastic",
    countertop_thickness_mm: 38,
  },
  required: {
    refrigerator: {
      mode: "built_in",
      freestanding_installation: "solo",
      width_mm: 600,
      depth_mm: 650,
      height_mm: 2000,
      gap_mm: 20,
    },
    oven: {
      placement: "under_counter",
    },
    sink: {
      width_mm: 600,
    },
    hood: {
      type: "built_in",
      width_mm: 600,
    },
    microwave: {
      type: "upper_built_in",
      width_mm: 600,
      height_mm: 400,
    },
    hob: {
      cabinet_width_mm: 600,
    },
  },
  optional: {
    dishwasher: {
      enabled: false,
      width_mm: 600,
    },
    undercounter_fridge: {
      enabled: false,
    },
  },
  locked: {},
};

function renderAdjustmentValue(adjustment: SizeAdjustment) {
  if (
    typeof adjustment.from_mm === "number" &&
    typeof adjustment.to_mm === "number"
  ) {
    return (
      <>
        {adjustment.from_mm} мм →{" "}
        <span className="font-semibold">{adjustment.to_mm} мм</span>
      </>
    );
  }

  return (
    <>
      {adjustment.from_value} →{" "}
      <span className="font-semibold">{adjustment.to_value}</span>
    </>
  );
}

function getLockedFieldLabels(options: KitchenOptions) {
  const labels: Record<string, string> = {
    "room.layout_shape": "форма кухни",
    "room.wall_length_mm": "ширина кухни",
    "room.side_1_width_mm": "сторона 1",
    "room.side_2_width_mm": "сторона 2",
    "room.kitchen_height_mm": "высота кухни",
    "room.wall_cabinets_enabled": "навесные шкафы",
    "room.mezzanine_enabled": "антресоли",
    "room.upper_cabinet_opening": "открывание верхних шкафов",
    "room.ceiling_type": "тип потолка",
    "room.entry_side": "вывод воды",
    "refrigerator.mode": "холодильник",
    "refrigerator.freestanding_installation": "тип отдельного холодильника",
    "oven.placement": "духовка",
    "sink.width_mm": "мойка",
    "hood.type": "вытяжка",
    "hood.width_mm": "ширина вытяжки",
    "microwave.type": "микроволновка",
    "hob.cabinet_width_mm": "варочная",
    "dishwasher.enabled": "посудомойка",
    "dishwasher.width_mm": "ширина посудомойки",
    "undercounter_fridge.enabled": "холодильник под столешницей",
  };

  const lockedFields = Object.keys(options.locked)
    .filter((field) => options.locked[field])
    .map((field) => labels[field] ?? field);

  return {
    lockedFields,
    autoFields:
      lockedFields.length > 0
        ? ["незафиксированные параметры подбирались автоматически"]
        : ["все вариативные параметры подбирались автоматически"],
  };
}

function mapGeneration(item: ApiGeneration): SavedGeneration {
  return {
    id: item.id,
    createdAt: item.created_at,
    title: item.title,
    shape: item.shape,
    widthLabel: item.width_label,
    autoFields: item.auto_fields ?? [],
    lockedFields: item.locked_fields ?? [],
    adjustmentCount: item.adjustment_count,
    details: item.details,
  };
}

function mapProfile(profile: ApiProfile): LocalUser {
  return {
    login: profile.login,
    history: profile.history.map(mapGeneration),
  };
}

export default function HomePage() {
  const [options, setOptions] = useState<KitchenOptions>(defaultOptions);
  const [notes, setNotes] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<LocalUser | null>(null);
  const [activeView, setActiveView] = useState<"planner" | "account">("planner");
  const [newPassword, setNewPassword] = useState("");
  const [accountMessage, setAccountMessage] = useState<string | null>(null);
  const [preferenceMessage, setPreferenceMessage] = useState<string | null>(null);
  const [generalSettingsOpen, setGeneralSettingsOpen] = useState(false);
  const [modulesSettingsOpen, setModulesSettingsOpen] = useState(false);

  useEffect(() => {
    const token = window.localStorage.getItem(SESSION_STORAGE_KEY);
    if (!token) {
      return;
    }

    void loadProfile(token);
  }, []);

  function updateRoom(patch: Partial<KitchenOptions["room"]>) {
    setOptions((current) => ({
      ...current,
      room: {
        ...current.room,
        ...patch,
      },
    }));
  }

  function updateRequired<K extends keyof KitchenOptions["required"]>(
    key: K,
    patch: Partial<KitchenOptions["required"][K]>
  ) {
    setOptions((current) => ({
      ...current,
      required: {
        ...current.required,
        [key]: {
          ...current.required[key],
          ...patch,
        },
      },
    }));
  }

  function updateOptional<K extends keyof KitchenOptions["optional"]>(
    key: K,
    patch: Partial<KitchenOptions["optional"][K]>
  ) {
    setOptions((current) => ({
      ...current,
      optional: {
        ...current.optional,
        [key]: {
          ...current.optional[key],
          ...patch,
        },
      },
    }));
  }

  function updateLocked(field: string, value: boolean) {
    setOptions((current) => ({
      ...current,
      locked: {
        ...current.locked,
        [field]: value,
      },
    }));
  }

  function unlockField(field: string) {
    updateLocked(field, false);
  }

  function appendPreferencePhrase(field: string, patch: Record<string, unknown>) {
    const phrase = manualPreferencePhrase(field, patch);
    if (!phrase) {
      return;
    }

    setNotes((current) => {
      if (current.includes(phrase)) {
        return current;
      }
      return current.trim() ? `${current.trim()} ${phrase}` : phrase;
    });
  }

  function updateRoomAndLock(
    field: string,
    patch: Partial<KitchenOptions["room"]>
  ) {
    appendPreferencePhrase(field, patch);
    setOptions((current) => ({
      ...current,
      room: {
        ...current.room,
        ...patch,
      },
      locked: {
        ...current.locked,
        [field]: true,
      },
    }));
  }

  function updateRequiredAndLock<K extends keyof KitchenOptions["required"]>(
    field: string,
    key: K,
    patch: Partial<KitchenOptions["required"][K]>
  ) {
    appendPreferencePhrase(field, patch);
    setOptions((current) => ({
      ...current,
      required: {
        ...current.required,
        [key]: {
          ...current.required[key],
          ...patch,
        },
      },
      locked: {
        ...current.locked,
        [field]: true,
      },
    }));
  }

  function updateOptionalAndLock<K extends keyof KitchenOptions["optional"]>(
    field: string,
    key: K,
    patch: Partial<KitchenOptions["optional"][K]>
  ) {
    appendPreferencePhrase(field, patch);
    setOptions((current) => ({
      ...current,
      optional: {
        ...current.optional,
        [key]: {
          ...current.optional[key],
          ...patch,
        },
      },
      locked: {
        ...current.locked,
        [field]: true,
      },
    }));
  }

  function applyPreferencePatchToOptions(
    current: KitchenOptions,
    payload: PreferenceParseResponse
  ) {
    const next: KitchenOptions = {
      ...current,
      room: { ...current.room },
      required: {
        ...current.required,
        refrigerator: { ...current.required.refrigerator },
        oven: { ...current.required.oven },
        sink: { ...current.required.sink },
        hood: { ...current.required.hood },
        microwave: { ...current.required.microwave },
        hob: { ...current.required.hob },
      },
      optional: {
        ...current.optional,
        dishwasher: { ...current.optional.dishwasher },
        undercounter_fridge: { ...current.optional.undercounter_fridge },
      },
      locked: { ...current.locked },
    };

    for (const [field, value] of Object.entries(payload.patch)) {
      switch (field) {
        case "room.layout_shape":
          next.room.layout_shape = value as KitchenOptions["room"]["layout_shape"];
          break;
        case "room.wall_cabinets_enabled":
          next.room.wall_cabinets_enabled = Boolean(value);
          break;
        case "room.mezzanine_enabled":
          next.room.mezzanine_enabled = Boolean(value);
          break;
        case "room.upper_cabinet_opening":
          next.room.upper_cabinet_opening =
            value as KitchenOptions["room"]["upper_cabinet_opening"];
          break;
        case "room.ceiling_type":
          next.room.ceiling_type = value as CeilingType;
          break;
        case "room.entry_side":
          next.room.entry_side = value as KitchenOptions["room"]["entry_side"];
          break;
        case "required.refrigerator.mode":
          next.required.refrigerator.mode =
            value as KitchenOptions["required"]["refrigerator"]["mode"];
          break;
        case "required.refrigerator.freestanding_installation":
          next.required.refrigerator.freestanding_installation =
            value as KitchenOptions["required"]["refrigerator"]["freestanding_installation"];
          break;
        case "required.oven.placement":
          next.required.oven.placement =
            value as KitchenOptions["required"]["oven"]["placement"];
          break;
        case "required.sink.width_mm":
          next.required.sink.width_mm = Number(value);
          break;
        case "required.hood.type":
          next.required.hood.type =
            value as KitchenOptions["required"]["hood"]["type"];
          break;
        case "required.hood.width_mm":
          next.required.hood.width_mm = Number(value);
          break;
        case "required.microwave.type":
          next.required.microwave.type =
            value as KitchenOptions["required"]["microwave"]["type"];
          break;
        case "required.microwave.width_mm":
          next.required.microwave.width_mm = Number(value);
          break;
        case "required.microwave.height_mm":
          next.required.microwave.height_mm = Number(value);
          break;
        case "required.hob.cabinet_width_mm":
          next.required.hob.cabinet_width_mm = Number(value);
          break;
        case "optional.dishwasher.enabled":
          next.optional.dishwasher.enabled = Boolean(value);
          break;
        case "optional.dishwasher.width_mm":
          next.optional.dishwasher.enabled = true;
          next.optional.dishwasher.width_mm = Number(value);
          break;
        case "optional.undercounter_fridge.enabled":
          next.optional.undercounter_fridge.enabled = Boolean(value);
          break;
      }

      next.locked[lockKeyFromPreferenceField(field)] = true;
    }

    return next;
  }

  async function parsePreferenceText() {
    const text = notes.trim();
    if (!text) {
      return null;
    }

    setPreferenceMessage(null);

    try {
      const res = await fetch("/api/preferences/parse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = (await res.json()) as PreferenceParseResponse | { detail?: string };

      if (!res.ok || !("patch" in data)) {
        setPreferenceMessage(
          "detail" in data && data.detail
            ? data.detail
            : "Не удалось распознать пожелания."
        );
        return null;
      }

      return data;
    } catch (error) {
      setPreferenceMessage(
        error instanceof Error
          ? error.message
          : "Не удалось подключиться к распознаванию пожеланий."
      );
      return null;
    }
  }

  function isLocked(field: string) {
    return Boolean(options.locked[field]);
  }

  function getAuthToken() {
    return window.localStorage.getItem(SESSION_STORAGE_KEY);
  }

  async function loadProfile(token: string) {
    const res = await fetch("/api/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!res.ok) {
      window.localStorage.removeItem(SESSION_STORAGE_KEY);
      setCurrentUser(null);
      return;
    }

    const profile = (await res.json()) as ApiProfile;
    setCurrentUser(mapProfile(profile));
  }

  async function handleAuthSubmit(e: FormEvent) {
    e.preventDefault();
    setAuthError(null);

    const trimmedLogin = login.trim();
    if (!trimmedLogin || !password) {
      setAuthError("Введите логин и пароль.");
      return;
    }

    const res = await fetch(`/api/auth/${authMode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ login: trimmedLogin, password }),
    });

    if (!res.ok) {
      setAuthError(
        authMode === "register"
          ? "Не удалось создать пользователя. Возможно, такой логин уже занят."
          : "Неверный логин или пароль."
      );
      return;
    }

    const data = (await res.json()) as AuthResponse;
    window.localStorage.setItem(SESSION_STORAGE_KEY, data.access_token);
    setCurrentUser({ login: data.user.login, history: [] });
    setPassword("");
    await loadProfile(data.access_token);
  }

  function logout() {
    window.localStorage.removeItem(SESSION_STORAGE_KEY);
    setCurrentUser(null);
    setActiveView("planner");
    setResult(null);
  }

  async function changePassword(e: FormEvent) {
    e.preventDefault();
    const token = getAuthToken();
    if (!currentUser || !token) {
      return;
    }

    if (newPassword.length < 4) {
      setAccountMessage("Пароль должен быть не короче 4 символов.");
      return;
    }

    const res = await fetch("/api/auth/change-password", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ new_password: newPassword }),
    });

    if (!res.ok) {
      setAccountMessage("Не удалось обновить пароль.");
      return;
    }

    setNewPassword("");
    setAccountMessage("Пароль обновлён.");
  }

  async function clearGenerationHistory() {
    const token = getAuthToken();
    if (!currentUser || !token || currentUser.history.length === 0) {
      return;
    }

    const confirmed = window.confirm(
      "Очистить всю историю генераций? Это действие нельзя отменить."
    );
    if (!confirmed) {
      return;
    }

    const res = await fetch("/api/generations", {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!res.ok) {
      setAccountMessage("Не удалось очистить историю.");
      return;
    }

    setCurrentUser({ ...currentUser, history: [] });
    setAccountMessage("История генераций очищена.");
  }

  async function loadGenerationFromHistory(item: SavedGeneration) {
    const savedResult = item.details?.result;
    if (savedResult?.generated_layout) {
      setOptions(savedResult.module_options);
      setResult(savedResult);
      setGenerationError(null);
      setActiveView("planner");
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }

    const savedOptions = item.details?.module_options;
    if (!savedOptions) {
      setAccountMessage("Для этой записи нет сохранённых чертежей.");
      return;
    }

    setLoading(true);
    setGenerationError(null);
    try {
      const res = await fetch("/api/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt:
            savedOptions.room.layout_shape === "corner"
              ? `Угловая кухня ${savedOptions.room.side_1_width_mm} x ${savedOptions.room.side_2_width_mm} мм.`
              : `Кухня ${savedOptions.room.wall_length_mm} мм.`,
          module_options: savedOptions,
        }),
      });

      const data = (await res.json()) as Result | PlanError;
      if (!res.ok || !("generated_layout" in data) || !data.generated_layout) {
        setAccountMessage("Не удалось загрузить чертежи этой итерации.");
        return;
      }

      setOptions(savedOptions);
      setResult(data);
      setActiveView("planner");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } finally {
      setLoading(false);
    }
  }

  async function deleteGenerationFromHistory(item: SavedGeneration) {
    const token = getAuthToken();
    if (!currentUser || !token) {
      return;
    }

    const confirmed = window.confirm("Удалить эту итерацию из истории?");
    if (!confirmed) {
      return;
    }

    const res = await fetch(`/api/generations/${item.id}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!res.ok) {
      setAccountMessage("Не удалось удалить запись истории.");
      return;
    }

    setCurrentUser({
      ...currentUser,
      history: currentUser.history.filter((entry) => entry.id !== item.id),
    });
    setAccountMessage("Итерация удалена из истории.");
  }

  async function saveGenerationToHistory(data: Result) {
    const token = getAuthToken();
    if (!currentUser || !token) {
      return;
    }

    const { lockedFields, autoFields } = getLockedFieldLabels(options);
    const widthLabel =
      options.room.layout_shape === "corner"
        ? `${options.room.side_1_width_mm} x ${options.room.side_2_width_mm} мм`
        : `${options.room.wall_length_mm} мм`;

    const res = await fetch("/api/generations", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        title:
          options.room.layout_shape === "corner"
            ? "Угловая кухня"
            : "Прямая кухня",
        shape: options.room.layout_shape,
        width_label: widthLabel,
        auto_fields: autoFields,
        locked_fields: lockedFields,
        adjustment_count: data.generated_layout.size_adjustments?.length ?? 0,
        details: {
          result: data,
          module_options: options,
          size_adjustments: data.generated_layout.size_adjustments ?? [],
          warnings: data.generated_layout.warnings ?? [],
        },
      }),
    });

    if (!res.ok) {
      return;
    }

    const saved = (await res.json()) as ApiGeneration;
    setCurrentUser({
      ...currentUser,
      history: [mapGeneration(saved), ...currentUser.history].slice(0, 30),
    });
  }
  function applySizeAdjustmentsToForm(data: Result) {
    const adjustments = data.generated_layout.size_adjustments ?? [];

    if (adjustments.length === 0) {
      return;
    }

    setOptions((current) => {
      let nextSinkWidth = current.required.sink.width_mm;
      let nextWallLength = current.room.wall_length_mm;
      let nextSide1Width = current.room.side_1_width_mm;
      let nextSide2Width = current.room.side_2_width_mm;
      let nextHobWidth = current.required.hob.cabinet_width_mm;
      let nextRefrigeratorMode = current.required.refrigerator.mode;
      let nextFreestandingInstallation =
        current.required.refrigerator.freestanding_installation;
      let nextHoodType = current.required.hood.type;
      let nextHoodWidth = current.required.hood.width_mm;
      let nextWallCabinetsEnabled = current.room.wall_cabinets_enabled;
      let nextMezzanineEnabled = current.room.mezzanine_enabled;
      let nextKitchenHeight = current.room.kitchen_height_mm;
      let nextOvenPlacement = current.required.oven.placement;
      let nextMicrowaveType = current.required.microwave.type;
      let nextMicrowaveWidth = current.required.microwave.width_mm;
      let nextMicrowaveHeight = current.required.microwave.height_mm;
      let nextDishwasherWidth = current.optional.dishwasher.width_mm;
      let nextDishwasherEnabled = current.optional.dishwasher.enabled;

      for (const adjustment of adjustments) {
        if (
          current.locked[adjustment.field] &&
          !(
            adjustment.field === "room.mezzanine_enabled" &&
            adjustment.reason === "freestanding_solo_fridge"
          )
        ) {
          continue;
        }

        if (
          adjustment.field === "room.wall_cabinets_enabled" &&
          typeof adjustment.to_value === "string"
        ) {
          nextWallCabinetsEnabled = adjustment.to_value.includes("включ");
        }

        if (
          adjustment.field === "room.mezzanine_enabled" &&
          typeof adjustment.to_value === "string"
        ) {
          nextMezzanineEnabled = adjustment.to_value.includes("\u0432\u043a\u043b\u044e\u0447");
        }

        if (
          adjustment.field === "room.wall_length_mm" &&
          typeof adjustment.to_mm === "number"
        ) {
          nextWallLength = adjustment.to_mm;
          nextSide1Width = adjustment.to_mm;
        }

        if (
          adjustment.field === "room.kitchen_height_mm" &&
          typeof adjustment.to_mm === "number"
        ) {
          nextKitchenHeight = adjustment.to_mm;
        }

        if (
          adjustment.field === "refrigerator.mode" &&
          typeof adjustment.to_value === "string"
        ) {
          nextRefrigeratorMode = adjustment.to_value.includes("встра")
            ? "built_in"
            : "freestanding";
        }

        if (
          adjustment.field === "refrigerator.freestanding_installation" &&
          typeof adjustment.to_value === "string"
        ) {
          nextFreestandingInstallation = adjustment.to_value.includes("корпус")
            ? "in_cabinet"
            : "solo";
        }

        if (
          adjustment.field === "hood.type" &&
          typeof adjustment.to_value === "string"
        ) {
          nextHoodType = adjustment.to_value.includes("встро")
            ? "built_in"
            : "solo";
        }

        if (
          adjustment.field === "hood.width_mm" &&
          typeof adjustment.to_mm === "number"
        ) {
          nextHoodWidth = adjustment.to_mm;
        }

        if (
          adjustment.field === "sink.width_mm" &&
          typeof adjustment.to_mm === "number"
        ) {
          nextSinkWidth = adjustment.to_mm;
        }

        if (
          adjustment.field === "dishwasher.width_mm" &&
          typeof adjustment.to_mm === "number"
        ) {
          nextDishwasherWidth = adjustment.to_mm;
          nextDishwasherEnabled = true;
        }

        if (
          adjustment.field === "hob.cabinet_width_mm" &&
          typeof adjustment.to_mm === "number"
        ) {
          nextHobWidth = adjustment.to_mm;
        }

        if (
          adjustment.field === "oven.placement" &&
          typeof adjustment.to_value === "string"
        ) {
          nextOvenPlacement = adjustment.to_value.includes("колон")
            ? "column"
            : "under_counter";
        }

        if (
          adjustment.field === "microwave.type" &&
          typeof adjustment.to_value === "string"
        ) {
          nextMicrowaveType = adjustment.to_value.includes("\u0432\u043a\u043b\u044e\u0447")
            ? "upper_built_in"
            : adjustment.to_value.includes("\u0432\u043a\u043b\u044e\u0447")
              ? "built_in"
              : "solo";

          if (
            nextMicrowaveType === "built_in" ||
            nextMicrowaveType === "upper_built_in"
          ) {
            nextMicrowaveWidth = 600;
            nextMicrowaveHeight = 400;
          } else {
            nextMicrowaveWidth = 450;
            nextMicrowaveHeight = 250;
          }
        }

        if (
          adjustment.field === "microwave.width_mm" &&
          typeof adjustment.to_mm === "number"
        ) {
          nextMicrowaveWidth = adjustment.to_mm;
        }

        if (
          adjustment.field === "microwave.height_mm" &&
          typeof adjustment.to_mm === "number"
        ) {
          nextMicrowaveHeight = adjustment.to_mm;
        }
      }

      return {
        ...current,
        room: {
          ...current.room,
          wall_length_mm: nextWallLength,
          side_1_width_mm: nextSide1Width,
          side_2_width_mm: nextSide2Width,
          wall_cabinets_enabled: nextWallCabinetsEnabled,
          mezzanine_enabled: nextMezzanineEnabled,
          kitchen_height_mm: nextKitchenHeight,
        },
        required: {
          ...current.required,
          sink: {
            ...current.required.sink,
            width_mm: nextSinkWidth,
          },
          refrigerator: {
            ...current.required.refrigerator,
            mode: nextRefrigeratorMode,
            freestanding_installation: nextFreestandingInstallation,
          },
          hood: {
            ...current.required.hood,
            type: nextHoodType,
            width_mm: nextHoodWidth,
          },
          oven: {
            ...current.required.oven,
            placement: nextOvenPlacement,
          },
          microwave: {
            ...current.required.microwave,
            type: nextMicrowaveType,
            width_mm: nextMicrowaveWidth,
            height_mm: nextMicrowaveHeight,
          },
          hob: {
            ...current.required.hob,
            cabinet_width_mm: nextHobWidth,
          },
        },
        optional: {
          ...current.optional,
          dishwasher: {
            ...current.optional.dishwasher,
            enabled: nextDishwasherEnabled,
            width_mm: nextDishwasherWidth,
          },
        },
      };
    });
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setGenerationError(null);

    try {
      let optionsForGeneration = options;
      const preferencePatch = await parsePreferenceText();

      if (preferencePatch && Object.keys(preferencePatch.patch).length > 0) {
        optionsForGeneration = applyPreferencePatchToOptions(
          optionsForGeneration,
          preferencePatch
        );
        setOptions(optionsForGeneration);
      }

      const res = await fetch("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt:
          optionsForGeneration.room.layout_shape === "corner"
            ? `Угловая кухня ${optionsForGeneration.room.side_1_width_mm} x ${optionsForGeneration.room.side_2_width_mm} мм. ${notes}`
            : `Кухня ${optionsForGeneration.room.wall_length_mm} мм. ${notes}`,
        module_options: optionsForGeneration,
      }),
    });

      const data = (await res.json()) as Result | PlanError;

      if (!res.ok || !("generated_layout" in data) || !data.generated_layout) {
        const errorData = data as PlanError;

        setResult(null);
        setGenerationError(
          [errorData.error, errorData.detail].filter(Boolean).join(": ") ||
            "Generation failed"
        );
        return;
      }

      setResult(data);
      void saveGenerationToHistory(data);
    } catch (error) {
      setResult(null);
      setGenerationError(
        error instanceof Error ? error.message : "Generation failed"
      );
    } finally {
      setLoading(false);
    }
  }

  function downloadBlob(filename: string, blob: Blob) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function downloadPng(filename: string, svg: string | undefined) {
    if (!svg) {
      return;
    }

    const svgBlob = new Blob([svg], {
      type: "image/svg+xml;charset=utf-8",
    });
    const url = URL.createObjectURL(svgBlob);
    const image = new Image();

    image.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = image.naturalWidth || image.width;
      canvas.height = image.naturalHeight || image.height;

      const context = canvas.getContext("2d");
      if (!context) {
        URL.revokeObjectURL(url);
        return;
      }

      context.fillStyle = "#ffffff";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0);
      URL.revokeObjectURL(url);

      canvas.toBlob((blob) => {
        if (!blob) {
          return;
        }

        downloadBlob(filename, blob);
      }, "image/png");
    };

    image.onerror = () => {
      URL.revokeObjectURL(url);
    };

    image.src = url;
  }

  function downloadAllViews(currentResult: Result) {
    const views = [
      ["kitchen_top_view.png", currentResult.top_view_svg],
      ["kitchen_front_view.png", currentResult.front_view_svg],
      ["kitchen_side_view.png", currentResult.side_view_svg],
    ] as const;

    views.forEach(([filename, svg], index) => {
      if (!svg) {
        return;
      }

      window.setTimeout(() => downloadPng(filename, svg), index * 160);
    });
  }

  const hoodSelectValue = hoodPresetWidths.includes(
    options.required.hood.width_mm
  )
    ? String(options.required.hood.width_mm)
    : "custom";

  const currentCountertopThicknessOptions = useMemo(
    () => countertopThicknessOptions[options.room.countertop_material],
    [options.room.countertop_material]
  );

  const countertopThicknessSelectValue = currentCountertopThicknessOptions.includes(
    options.room.countertop_thickness_mm
  )
    ? String(options.room.countertop_thickness_mm)
    : "custom";

  const appHeader = currentUser ? (
    <header className="border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-4">
        <button
          type="button"
          className="text-left"
          onClick={() => setActiveView("planner")}
        >
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
            Kitchen Planner
          </p>
          <h1 className="text-2xl font-bold text-slate-950">
            Автоматизированное проектирование кухни
          </h1>
        </button>

        <div className="flex flex-wrap items-center gap-3">
          <span className="rounded-full bg-slate-100 px-4 py-2 text-sm text-slate-700">
            {currentUser.login}
          </span>
          <button
            type="button"
            className={`rounded-full px-4 py-2 text-sm font-semibold ${
              activeView === "planner"
                ? "bg-slate-900 text-white"
                : "border border-slate-300 bg-white text-slate-700"
            }`}
            onClick={() => setActiveView("planner")}
          >
            Планировщик
          </button>
          <button
            type="button"
            className={`rounded-full px-4 py-2 text-sm font-semibold ${
              activeView === "account"
                ? "bg-slate-900 text-white"
                : "border border-slate-300 bg-white text-slate-700"
            }`}
            onClick={() => setActiveView("account")}
          >
            Личный кабинет
          </button>
          <button
            type="button"
            className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700"
            onClick={logout}
          >
            Выйти
          </button>
        </div>
      </div>
    </header>
  ) : null;

  if (!currentUser) {
    return (
      <main className="min-h-screen bg-[#f6f3ee] text-slate-950">
        <div className="mx-auto grid min-h-screen max-w-6xl items-center gap-10 px-6 py-10 lg:grid-cols-[1.05fr_0.95fr]">
          <section className="space-y-7">
            <div className="inline-flex rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-600 shadow-sm">
              Kitchen Planner
            </div>
            <div className="space-y-4">
              <h1 className="max-w-3xl text-4xl font-bold leading-tight text-slate-950 md:text-5xl">
                Подбор кухонного гарнитура по правилам и ограничениям
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-slate-600">
                Войдите, чтобы генерировать прямые и угловые кухни, скачивать
                отрисовки и хранить историю расчётов в личном кабинете.
              </p>
            </div>
            <div className="grid gap-3 text-sm text-slate-600 sm:grid-cols-3">
              <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                SVG-рендеры с размерными линиями
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                Автоматические корректировки модулей
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                История генераций пользователя
              </div>
            </div>
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-xl shadow-slate-200/70">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-slate-950">
                {authMode === "login" ? "Вход" : "Регистрация"}
              </h2>
              <p className="mt-2 text-sm text-slate-500">
                Серверная авторизация с хранением пользователей в PostgreSQL.
              </p>
            </div>

            <form onSubmit={handleAuthSubmit} className="space-y-4">
              <label className="block">
                <span className="mb-1 block text-sm font-semibold text-slate-700">
                  Логин
                </span>
                <input
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  value={login}
                  onChange={(e) => setLogin(e.target.value)}
                  autoComplete="username"
                />
              </label>

              <label className="block">
                <span className="mb-1 block text-sm font-semibold text-slate-700">
                  Пароль
                </span>
                <input
                  type="password"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete={
                    authMode === "login" ? "current-password" : "new-password"
                  }
                />
              </label>

              {authError && (
                <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {authError}
                </p>
              )}

              <button className="w-full rounded-xl bg-slate-950 px-5 py-3 font-semibold text-white shadow-lg shadow-slate-300">
                {authMode === "login" ? "Войти" : "Создать аккаунт"}
              </button>
            </form>

            <button
              type="button"
              className="mt-5 w-full rounded-xl border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700"
              onClick={() => {
                setAuthMode(authMode === "login" ? "register" : "login");
                setAuthError(null);
              }}
            >
              {authMode === "login"
                ? "Зарегистрировать нового пользователя"
                : "Уже есть аккаунт? Войти"}
            </button>
          </section>
        </div>
      </main>
    );
  }

  if (activeView === "account") {
    return (
      <main className="min-h-screen bg-[#f6f3ee] text-slate-950">
        {appHeader}
        <div className="mx-auto max-w-7xl space-y-8 px-6 py-8">
          <section className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
            <h2 className="text-2xl font-bold">Личный кабинет</h2>
            <p className="mt-2 text-slate-600">
              Пользователь: <span className="font-semibold">{currentUser.login}</span>
            </p>

            <form onSubmit={changePassword} className="mt-6 max-w-xl space-y-4">
              <label className="block">
                <span className="mb-1 block text-sm font-semibold text-slate-700">
                  Новый пароль
                </span>
                <input
                  type="password"
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-slate-900"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  autoComplete="new-password"
                />
              </label>
              <button className="rounded-xl bg-slate-950 px-5 py-3 font-semibold text-white">
                Изменить пароль
              </button>
              {accountMessage && (
                <p className="text-sm font-semibold text-slate-600">
                  {accountMessage}
                </p>
              )}
            </form>
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-2xl font-bold">История генераций</h2>
              <button
                type="button"
                className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-950 disabled:cursor-not-allowed disabled:opacity-45"
                onClick={clearGenerationHistory}
                disabled={currentUser.history.length === 0}
              >
                Очистить историю
              </button>
            </div>
            {currentUser.history.length === 0 ? (
              <p className="mt-4 text-slate-500">
                История пока пустая. Сгенерируйте кухню, и расчёт появится здесь.
              </p>
            ) : (
              <div className="mt-5 grid gap-4">
                {currentUser.history.map((item) => (
                  <article
                    key={item.id}
                    className="rounded-2xl border border-slate-200 bg-slate-50 p-5"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <h3 className="text-lg font-bold">{item.title}</h3>
                        <p className="text-sm text-slate-500">
                          {new Date(item.createdAt).toLocaleString("ru-RU")} ·{" "}
                          {item.widthLabel}
                        </p>
                      </div>
                      <span className="rounded-full bg-white px-3 py-1 text-sm font-semibold text-slate-600">
                        Автоматических корректировок: {item.adjustmentCount}
                      </span>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white"
                        onClick={() => void loadGenerationFromHistory(item)}
                      >
                        Открыть эскизы
                      </button>
                      <button
                        type="button"
                        className="rounded-xl border border-rose-200 px-4 py-2 text-sm font-semibold text-rose-700 transition hover:border-rose-500"
                        onClick={() => void deleteGenerationFromHistory(item)}
                      >
                        Удалить генерацию
                      </button>
                    </div>
                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                      <div>
                        <p className="text-sm font-semibold text-slate-700">
                          Зафиксировано пользователем
                        </p>
                        <p className="mt-1 text-sm text-slate-600">
                          {item.lockedFields.length > 0
                            ? item.lockedFields.join(", ")
                            : "ничего не фиксировалось"}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-slate-700">
                          Подбиралось автоматически
                        </p>
                        <p className="mt-1 text-sm text-slate-600">
                          {item.autoFields.join(", ")}
                        </p>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#f6f3ee] text-slate-950">
      {appHeader}
      <div className="mx-auto max-w-7xl space-y-8 px-6 py-8">
        <section className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
          <h2 className="text-3xl font-bold">Планировщик кухни</h2>
          <p className="mt-2 max-w-3xl text-slate-600">
            Задайте параметры помещения и модулей. Всё, что пользователь выбирает
            вручную, считается зафиксированным, остальные параметры подбираются
            автоматически по правилам генератора.
          </p>
        </section>

      <form onSubmit={onSubmit} className="space-y-8">
        <section className="border rounded-xl p-5 space-y-4">
          <h2 className="text-xl font-semibold">Вариант кухни</h2>

          <label className="block">
            <span className="block mb-1">Форма</span>
            <select
              className="border rounded p-2 w-full"
              value={options.room.layout_shape}
              onChange={(e) =>
                updateRoom({
                  layout_shape: e.target.value as "straight" | "corner",
                })
              }
            >
              <option value="straight">Прямая</option>
              <option value="corner">Угловая</option>
            </select>
          </label>

          {options.room.layout_shape === "corner" && (
            <div className="grid md:grid-cols-2 gap-4">
              <label className="block">
                <span className="block mb-1">Ширина стороны 1, мм</span>
                <input
                  type="number"
                  className="border rounded p-2 w-full"
                  value={options.room.side_1_width_mm}
                  onChange={(e) =>
                    updateRoom({
                      side_1_width_mm: Number(e.target.value),
                      wall_length_mm: Number(e.target.value),
                    })
                  }
                />
              </label>

              <label className="block">
                <span className="block mb-1">Ширина стороны 2, мм</span>
                <input
                  type="number"
                  className="border rounded p-2 w-full"
                  value={options.room.side_2_width_mm}
                  onChange={(e) =>
                    updateRoom({ side_2_width_mm: Number(e.target.value) })
                  }
                />
              </label>
            </div>
          )}

          {options.room.layout_shape === "straight" && (
            <label className="block">
              <span className="block mb-1">Ширина кухни, мм</span>
              <input
                type="number"
                className="border rounded p-2 w-full"
                value={options.room.wall_length_mm}
                onChange={(e) =>
                  updateRoom({
                    wall_length_mm: Number(e.target.value),
                    side_1_width_mm: Number(e.target.value),
                  })
                }
              />
            </label>
          )}

          <label className="block">
            <span className="block mb-1">Высота кухни, мм</span>
            <input
              type="number"
              className="border rounded p-2 w-full"
              value={options.room.kitchen_height_mm}
              onChange={(e) =>
                updateRoom({ kitchen_height_mm: Number(e.target.value) })
              }
            />
          </label>
        </section>

        <section className="rounded-3xl border-2 border-slate-900 bg-white p-6 shadow-sm">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-2xl font-bold">Пожелания к кухне</h2>
              <p className="mt-1 max-w-3xl text-sm text-slate-600">
                Опишите параметры словами: система распознает пожелания и
                зафиксирует подходящие настройки в форме.
              </p>
            </div>
            <span className="rounded-full bg-slate-950 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-white">
              Ollama
            </span>
          </div>

          <label className="block">
            <textarea
              className="min-h-32 w-full rounded-2xl border border-slate-300 bg-slate-50 p-4 outline-none transition focus:border-slate-950 focus:bg-white"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Например: хочу угловую кухню, компактную посудомойку, мойку и варочную стандартного размера, подъёмные верхние шкафы и СВЧ в колонне."
            />
          </label>
          <p className="mt-4 text-sm text-slate-600">
            Локальная Ollama дополняет предметные правила распознавания при генерации.
          </p>
          {preferenceMessage && (
            <p className="mt-4 rounded-xl bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-700">
              {preferenceMessage}
            </p>
          )}
        </section>

        <section className="border rounded-xl p-5 space-y-4">
          <button
            type="button"
            className="flex w-full items-center justify-between gap-4 text-left"
            onClick={() => setGeneralSettingsOpen((current) => !current)}
          >
            <span>
              <span className="block text-xl font-semibold">Общие параметры</span>
              <span className="text-sm text-slate-500">
                Высота, верхние шкафы, потолок, вывод воды, рост и столешница.
              </span>
            </span>
            <span className="rounded-full border border-slate-300 px-3 py-1 text-sm font-semibold text-slate-700">
              {generalSettingsOpen ? "Свернуть" : "Развернуть"}
            </span>
          </button>

          {generalSettingsOpen && (
            <div className="space-y-4">

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={options.room.wall_cabinets_enabled}
              onChange={(e) =>
                updateRoom({ wall_cabinets_enabled: e.target.checked })
              }
            />
            <span>Навесные шкафы</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={options.room.mezzanine_enabled}
              disabled={!options.room.wall_cabinets_enabled}
              onChange={(e) =>
                updateRoomAndLock("room.mezzanine_enabled", {
                  mezzanine_enabled: e.target.checked,
                })
              }
            />
            <span>Антресольные шкафы</span>
          </label>

          <label className="block">
            <span className="block mb-1">Открывание верхних шкафов</span>

            <select
              className="border rounded p-2 w-full"
              value={options.room.upper_cabinet_opening ?? "hinged"}
              disabled={!options.room.wall_cabinets_enabled}
              onChange={(e) =>
                updateRoom({
                  upper_cabinet_opening: e.target.value as
                    | "hinged"
                    | "lift",
                })
              }
            >
              <option value="hinged">Распашные</option>
              <option value="lift">Подъёмные</option>
            </select>
          </label>

          <label className="block">
            <span className="block mb-1">Тип потолка</span>

            <select
              className="border rounded p-2 w-full"
              value={options.room.ceiling_type}
              disabled={
                !options.room.wall_cabinets_enabled ||
                !options.room.mezzanine_enabled
              }
              onChange={(e) =>
                updateRoom({ ceiling_type: e.target.value as CeilingType })
              }
            >
              <option value="stretch">Натяжной</option>
              <option value="plasterboard">Гипсокартонный</option>
            </select>
          </label>

          <label className="block">
            <span className="block mb-1">
              С какой стороны вывод воды?
            </span>

            <select
              className="border rounded p-2 w-full"
              value={options.room.entry_side}
              onChange={(e) =>
                updateRoom({
                  entry_side: e.target.value as "left" | "right",
                })
              }
            >
              <option value="left">Слева</option>
              <option value="right">Справа</option>
            </select>
          </label>

          <div className="border rounded-xl p-4 space-y-3">
            <h3 className="font-semibold">Рост заказчика</h3>

            <label className="block">
              <span className="block mb-1">Как указать рост?</span>
              <select
                className="border rounded p-2 w-full"
                value={options.room.customer_height_mode}
                onChange={(e) => {
                  const nextMode = e.target.value as CustomerHeightMode;

                  if (nextMode === "height_170_or_below") {
                    updateRoom({
                      customer_height_mode: nextMode,
                      customer_height_cm: 170,
                    });
                    return;
                  }

                  if (nextMode === "height_196_or_above") {
                    updateRoom({
                      customer_height_mode: nextMode,
                      customer_height_cm: 196,
                    });
                    return;
                  }

                  updateRoom({
                    customer_height_mode: nextMode,
                    customer_height_cm:
                      options.room.customer_height_cm < 150 ||
                      options.room.customer_height_cm > 196
                        ? 175
                        : options.room.customer_height_cm,
                  });
                }}
              >
                <option value="height_170_or_below">170 см и ниже</option>
                <option value="exact">Указать точный рост</option>
                <option value="height_196_or_above">196 см и выше</option>
              </select>
            </label>

            {options.room.customer_height_mode === "exact" && (
              <label className="block">
                <span className="block mb-1">Рост, см</span>
                <input
                  type="number"
                  min={150}
                  max={196}
                  className="border rounded p-2 w-full"
                  value={options.room.customer_height_cm}
                  onChange={(e) =>
                    updateRoom({
                      customer_height_cm: Number(e.target.value),
                    })
                  }
                />
                <span className="text-sm text-gray-500">
                  Можно указать любое значение от 150 до 196 см.
                </span>
              </label>
            )}
          </div>

          <div className="border rounded-xl p-4 space-y-3">
            <h3 className="font-semibold">Столешница</h3>

            <label className="block">
              <span className="block mb-1">Материал столешницы</span>
              <select
                className="border rounded p-2 w-full"
                value={options.room.countertop_material}
                onChange={(e) => {
                  const nextMaterial = e.target.value as CountertopMaterial;
                  const nextThicknessOptions =
                    countertopThicknessOptions[nextMaterial];
                  const currentThickness = options.room.countertop_thickness_mm;

                  let nextThickness = currentThickness;

                  if (!nextThicknessOptions.includes(currentThickness)) {
                    if (materialAllowsCustomThickness(nextMaterial)) {
                      nextThickness =
                        countertopCustomThicknessDefaults[nextMaterial] ??
                        nextThicknessOptions[0];
                    } else {
                      nextThickness = nextThicknessOptions[0];
                    }
                  }

                  updateRoom({
                    countertop_material: nextMaterial,
                    countertop_thickness_mm: nextThickness,
                  });
                }}
              >
                {(
                  Object.keys(countertopMaterialLabels) as CountertopMaterial[]
                ).map((material) => (
                  <option key={material} value={material}>
                    {countertopMaterialLabels[material]}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="block mb-1">Толщина столешницы, мм</span>
              <select
                className="border rounded p-2 w-full"
                value={countertopThicknessSelectValue}
                onChange={(e) => {
                  const value = e.target.value;
                  const material = options.room.countertop_material;

                  if (value === "custom") {
                    const customDefault =
                      countertopCustomThicknessDefaults[material] ??
                      options.room.countertop_thickness_mm;

                    updateRoom({
                      countertop_thickness_mm: customDefault,
                    });
                    return;
                  }

                  updateRoom({
                    countertop_thickness_mm: Number(value),
                  });
                }}
              >
                {currentCountertopThicknessOptions.map((thickness) => (
                  <option key={thickness} value={thickness}>
                    {thickness} мм
                  </option>
                ))}

                {materialAllowsCustomThickness(
                  options.room.countertop_material
                ) && <option value="custom">Произвольный размер</option>}
              </select>
            </label>

            {materialAllowsCustomThickness(options.room.countertop_material) &&
              !currentCountertopThicknessOptions.includes(
                options.room.countertop_thickness_mm
              ) && (
                <label className="block">
                  <span className="block mb-1">Свой размер, мм</span>
                  <input
                    type="number"
                    className="border rounded p-2 w-full"
                    value={options.room.countertop_thickness_mm}
                    onChange={(e) =>
                      updateRoom({
                        countertop_thickness_mm: Number(e.target.value),
                      })
                    }
                  />
                </label>
              )}
          </div>
            </div>
          )}
        </section>

        <section className="rounded-xl border p-5">
          <button
            type="button"
            className="flex w-full items-center justify-between gap-4 text-left"
            onClick={() => setModulesSettingsOpen((current) => !current)}
          >
            <span>
              <span className="block text-2xl font-semibold">
                Комплектация и техника
              </span>
              <span className="text-sm text-slate-500">
                Холодильник, духовка, мойка, вытяжка, СВЧ, варочная и дополнительные модули.
              </span>
            </span>
            <span className="rounded-full border border-slate-300 px-3 py-1 text-sm font-semibold text-slate-700">
              {modulesSettingsOpen ? "Свернуть" : "Развернуть"}
            </span>
          </button>

          {modulesSettingsOpen && (
            <div className="mt-5 space-y-6">

          <div className="grid md:grid-cols-2 gap-4">
            <div className="border rounded-xl p-5 space-y-3">
              <h3 className="font-semibold">Холодильник</h3>

              <label className="block">
                <span className="block mb-1">Тип</span>
                <select
                  className="border rounded p-2 w-full"
                  value={
                    isLocked("refrigerator.mode")
                      ? options.required.refrigerator.mode
                      : AUTO_SELECT_VALUE
                  }
                  onChange={(e) => {
                    if (e.target.value === AUTO_SELECT_VALUE) {
                      unlockField("refrigerator.mode");
                      return;
                    }

                    updateRequiredAndLock(
                      "refrigerator.mode",
                      "refrigerator",
                      {
                        mode: e.target.value as "built_in" | "freestanding",
                      }
                    );
                  }}
                >
                  <option value={AUTO_SELECT_VALUE}>Авто</option>
                  <option value="built_in">Встраиваемый</option>
                  <option value="freestanding">Отдельно стоящий</option>
                </select>
              </label>


              {options.required.refrigerator.mode === "freestanding" && (
                <>
                  <label className="block">
                    <span className="block mb-1">Как ставим</span>
                    <select
                      className="border rounded p-2 w-full"
                      value={
                        options.required.refrigerator.freestanding_installation
                      }
                      onChange={(e) =>
                        updateRequiredAndLock(
                          "refrigerator.freestanding_installation",
                          "refrigerator",
                          {
                          freestanding_installation: e.target.value as
                            | "in_cabinet"
                            | "solo",
                          }
                        )
                      }
                    >
                      <option value="in_cabinet">
                        Внутри мебельного каркаса
                      </option>
                      <option value="solo">Соло рядом с кухней</option>
                    </select>
                  </label>

                  <div className="grid grid-cols-2 gap-3">
                    <label>
                      <span className="block mb-1">Ширина, мм</span>
                      <input
                        type="number"
                        className="border rounded p-2 w-full"
                        value={options.required.refrigerator.width_mm}
                        onChange={(e) =>
                          updateRequired("refrigerator", {
                            width_mm: Number(e.target.value),
                          })
                        }
                      />
                    </label>

                    <label>
                      <span className="block mb-1">Глубина, мм</span>
                      <input
                        type="number"
                        className="border rounded p-2 w-full"
                        value={options.required.refrigerator.depth_mm}
                        onChange={(e) =>
                          updateRequired("refrigerator", {
                            depth_mm: Number(e.target.value),
                          })
                        }
                      />
                    </label>

                    <label>
                      <span className="block mb-1">Высота, мм</span>
                      <input
                        type="number"
                        className="border rounded p-2 w-full"
                        value={options.required.refrigerator.height_mm}
                        onChange={(e) =>
                          updateRequired("refrigerator", {
                            height_mm: Number(e.target.value),
                          })
                        }
                      />
                    </label>

                    <label>
                      <span className="block mb-1">Зазор, мм</span>
                      <input
                        type="number"
                        className="border rounded p-2 w-full"
                        value={options.required.refrigerator.gap_mm}
                        onChange={(e) =>
                          updateRequired("refrigerator", {
                            gap_mm: Number(e.target.value),
                          })
                        }
                      />
                    </label>
                  </div>
                </>
              )}
            </div>

            <div className="border rounded-xl p-5 space-y-3">
              <h3 className="font-semibold">Духовка</h3>

              <label className="block">
                <span className="block mb-1">Расположение</span>
                <select
                  className="border rounded p-2 w-full"
                  value={
                    isLocked("oven.placement")
                      ? options.required.oven.placement
                      : AUTO_SELECT_VALUE
                  }
                  onChange={(e) => {
                    if (e.target.value === AUTO_SELECT_VALUE) {
                      unlockField("oven.placement");
                      return;
                    }

                    updateRequiredAndLock("oven.placement", "oven", {
                      placement: e.target.value as "under_counter" | "column",
                    });
                  }}
                >
                  <option value={AUTO_SELECT_VALUE}>Авто</option>
                  <option value="under_counter">Под столешницей</option>
                  <option value="column">В колонне</option>
                </select>
              </label>
            </div>

            <div className="border rounded-xl p-5 space-y-3">
              <h3 className="font-semibold">Мойка</h3>

              <label className="block">
                <span className="block mb-1">Размер тумбы, мм</span>
                <select
                  className="border rounded p-2 w-full"
                  value={
                    isLocked("sink.width_mm")
                      ? options.required.sink.width_mm
                      : AUTO_SELECT_VALUE
                  }
                  onChange={(e) => {
                    if (e.target.value === AUTO_SELECT_VALUE) {
                      unlockField("sink.width_mm");
                      return;
                    }

                    updateRequiredAndLock("sink.width_mm", "sink", {
                      width_mm: Number(e.target.value),
                    });
                  }}
                >
                  <option value={AUTO_SELECT_VALUE}>Авто</option>
                  <option value={400}>400</option>
                  <option value={450}>450</option>
                  <option value={500}>500</option>
                  <option value={600}>600</option>
                  <option value={800}>800</option>
                  <option value={900}>900</option>
                  <option value={1000}>1000</option>
                  <option value={1200}>1200</option>
                </select>
              </label>
            </div>

            <div className="border rounded-xl p-5 space-y-3">
              <h3 className="font-semibold">Вытяжка</h3>

              <label className="block">
                <span className="block mb-1">Тип</span>
                <select
                  className="border rounded p-2 w-full"
                  value={
                    isLocked("hood.type")
                      ? options.required.hood.type
                      : AUTO_SELECT_VALUE
                  }
                  onChange={(e) => {
                    if (e.target.value === AUTO_SELECT_VALUE) {
                      unlockField("hood.type");
                      return;
                    }

                    const nextType = e.target.value as "built_in" | "solo";
                    const currentWidth = options.required.hood.width_mm;
                    const nextWidth = hoodPresetWidths.includes(currentWidth)
                      ? currentWidth
                      : 600;

                    updateRequiredAndLock("hood.type", "hood", {
                      type: nextType,
                      width_mm: nextWidth,
                    });
                    if (nextType === "solo") {
                      updateRoomAndLock("room.wall_cabinets_enabled", {
                        wall_cabinets_enabled: false,
                      });
                    }
                  }}
                >
                  <option value={AUTO_SELECT_VALUE}>Авто</option>
                  <option value="built_in">Встраиваемая</option>
                  <option value="solo">Соло модель</option>
                </select>
              </label>

              <label className="block">
                <span className="block mb-1">Ширина, мм</span>
                <select
                  className="border rounded p-2 w-full"
                  value={
                    isLocked("hood.width_mm")
                      ? options.required.hood.type === "solo"
                        ? hoodSelectValue
                        : String(options.required.hood.width_mm)
                      : AUTO_SELECT_VALUE
                  }
                  onChange={(e) => {
                    if (e.target.value === AUTO_SELECT_VALUE) {
                      unlockField("hood.width_mm");
                      return;
                    }

                    if (e.target.value === "custom") {
                      updateRequiredAndLock("hood.width_mm", "hood", {
                        width_mm: 1000,
                      });
                    } else {
                      updateRequiredAndLock("hood.width_mm", "hood", {
                        width_mm: Number(e.target.value),
                      });
                    }
                  }}
                >
                  <option value={AUTO_SELECT_VALUE}>Авто</option>
                  <option value={600}>600</option>
                  <option value={900}>900</option>
                  <option value={1200}>1200</option>
                  <option value={1800}>1800</option>
                  {options.required.hood.type === "solo" && (
                    <option value="custom">Свой размер</option>
                  )}
                </select>
              </label>

              {options.required.hood.type === "solo" &&
                isLocked("hood.width_mm") &&
                !hoodPresetWidths.includes(options.required.hood.width_mm) && (
                  <label className="block">
                    <span className="block mb-1">Свой размер, мм</span>
                    <input
                      type="number"
                      className="border rounded p-2 w-full"
                      value={options.required.hood.width_mm}
                      onChange={(e) =>
                        updateRequiredAndLock("hood.width_mm", "hood", {
                          width_mm: Number(e.target.value),
                        })
                      }
                    />
                  </label>
                )}
            </div>

            <div className="border rounded-xl p-5 space-y-3">
              <h3 className="font-semibold">Микроволновка</h3>

              <label className="block">
                <span className="block mb-1">Тип</span>
                <select
                  className="border rounded p-2 w-full"
                  value={
                    isLocked("microwave.type")
                      ? options.required.microwave.type
                      : AUTO_SELECT_VALUE
                  }
                  onChange={(e) => {
                    if (e.target.value === AUTO_SELECT_VALUE) {
                      unlockField("microwave.type");
                      return;
                    }

                    const nextType = e.target.value as
                      | "built_in"
                      | "upper_built_in"
                      | "solo";

                    if (nextType === "built_in" || nextType === "upper_built_in") {
                      updateRequiredAndLock("microwave.type", "microwave", {
                        type: nextType,
                        width_mm: 600,
                        height_mm: 400,
                      });
                    } else {
                      updateRequiredAndLock("microwave.type", "microwave", {
                        type: "solo",
                        width_mm: 450,
                        height_mm: 250,
                      });
                    }
                  }}
                >
                  <option value={AUTO_SELECT_VALUE}>Авто</option>
                  <option value="upper_built_in">В навесном шкафу</option>
                  <option value="built_in">В колонне</option>
                  <option value="solo">Соло</option>
                </select>
              </label>

              {isLocked("microwave.type") &&
                (options.required.microwave.type === "built_in" ||
                  options.required.microwave.type === "upper_built_in") && (
                  <label className="block">
                    <span className="block mb-1">Высота, мм</span>
                    <input
                      type="number"
                      className="border rounded p-2 w-full"
                      value={options.required.microwave.height_mm}
                      onChange={(e) =>
                        updateRequiredAndLock("microwave.height_mm", "microwave", {
                          height_mm: Number(e.target.value),
                        })
                      }
                    />
                  </label>
                )}

              {isLocked("microwave.type") && options.required.microwave.type === "solo" && (
                <div className="grid grid-cols-2 gap-3">
                  <label>
                    <span className="block mb-1">Ширина, мм</span>
                    <input
                      type="number"
                      className="border rounded p-2 w-full"
                      value={options.required.microwave.width_mm}
                      onChange={(e) =>
                        updateRequiredAndLock("microwave.width_mm", "microwave", {
                          width_mm: Number(e.target.value),
                        })
                      }
                    />
                  </label>

                  <label>
                    <span className="block mb-1">Высота, мм</span>
                    <input
                      type="number"
                      className="border rounded p-2 w-full"
                      value={options.required.microwave.height_mm}
                      onChange={(e) =>
                        updateRequiredAndLock("microwave.height_mm", "microwave", {
                          height_mm: Number(e.target.value),
                        })
                      }
                    />
                  </label>
                </div>
              )}
            </div>

            <div className="border rounded-xl p-5 space-y-3">
              <h3 className="font-semibold">Варочная панель</h3>

              <label className="block">
                <span className="block mb-1">Ширина варочной поверхности, мм</span>
                <select
                  className="border rounded p-2 w-full"
                  value={
                    isLocked("hob.cabinet_width_mm")
                      ? options.required.hob.cabinet_width_mm
                      : AUTO_SELECT_VALUE
                  }
                  onChange={(e) => {
                    if (e.target.value === AUTO_SELECT_VALUE) {
                      unlockField("hob.cabinet_width_mm");
                      return;
                    }

                    updateRequiredAndLock("hob.cabinet_width_mm", "hob", {
                      cabinet_width_mm: Number(e.target.value),
                    });
                  }}
                >
                  <option value={AUTO_SELECT_VALUE}>Авто</option>
                  <option value={300}>300</option>
                  <option value={600}>600</option>
                  <option value={800}>800</option>
                  <option value={900}>900</option>
                </select>
              </label>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-4">
            <div className="border rounded-xl p-5 space-y-3">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={options.optional.dishwasher.enabled}
                  onChange={(e) => {
                    if (!e.target.checked) {
                      updateOptional("dishwasher", { enabled: false });
                      unlockField("dishwasher.width_mm");
                      return;
                    }

                    updateOptional("dishwasher", {
                      enabled: true,
                    });
                  }}
                />
                <span className="font-semibold">Посудомоечная машина</span>
              </label>

              <label className="block">
                <span className="block mb-1">Ширина</span>
                <select
                  className="border rounded p-2 w-full"
                  value={
                    isLocked("dishwasher.width_mm")
                      ? options.optional.dishwasher.width_mm
                      : AUTO_SELECT_VALUE
                  }
                  onChange={(e) => {
                    if (e.target.value === AUTO_SELECT_VALUE) {
                      unlockField("dishwasher.width_mm");
                      return;
                    }

                    updateOptionalAndLock("dishwasher.width_mm", "dishwasher", {
                      width_mm: Number(e.target.value),
                    });
                  }}
                >
                  <option value={AUTO_SELECT_VALUE}>Авто</option>
                  <option value={600}>60 см</option>
                  <option value={450}>45 см</option>
                </select>
              </label>
            </div>

            <div className="border rounded-xl p-5">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={options.optional.undercounter_fridge.enabled}
                  onChange={(e) =>
                    updateOptional("undercounter_fridge", {
                      enabled: e.target.checked,
                    })
                  }
                />
                <span className="font-semibold">
                  Холодильник под столешницей 600 мм
                </span>
              </label>
            </div>

          </div>
            </div>
          )}
        </section>

        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <button
            className="group flex w-full items-center justify-center gap-3 rounded-2xl bg-slate-950 px-8 py-5 text-lg font-bold text-white shadow-lg shadow-slate-300 transition hover:-translate-y-0.5 hover:bg-slate-800 hover:shadow-xl disabled:cursor-not-allowed disabled:translate-y-0 disabled:bg-slate-400 disabled:shadow-none"
            disabled={loading}
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white text-slate-950 transition group-hover:scale-105">
              {loading ? "..." : "→"}
            </span>
            {loading ? "Генерирую кухню..." : "Сгенерировать кухню"}
          </button>
          <p className="mt-3 text-center text-sm text-slate-500">
            Пожелания текстом и выбранные параметры будут применены автоматически.
          </p>
        </div>
      </form>

      {generationError && (
        <section className="border border-red-300 bg-red-50 p-4 rounded-xl">
          <h2 className="font-semibold text-red-800 mb-2">
            Ошибка генерации
          </h2>
          <p className="text-red-700 whitespace-pre-wrap">{generationError}</p>
        </section>
      )}

      {result && (
        <section className="space-y-6">
          <div className="border rounded-xl p-5 bg-gray-50">
            <button
              type="button"
              className="px-4 py-2 rounded-lg border font-semibold bg-white"
              onClick={() => downloadAllViews(result)}
            >
              Скачать все отрисовки
            </button>
          </div>

          {result.generated_layout.warnings?.length > 0 && (
            <div className="border border-red-300 bg-red-50 p-4 rounded-xl">
              {result.generated_layout.warnings.map((warning, index) => (
                <p key={index} className="text-red-700">
                  {warning}
                </p>
              ))}
            </div>
          )}

          {result.generated_layout.size_adjustments &&
            result.generated_layout.size_adjustments.length > 0 && (
              <div className="border border-yellow-300 bg-yellow-50 p-4 rounded-xl">
                <h2 className="font-semibold mb-2">
                  Автоматически изменённые размеры
                </h2>

                <div className="space-y-1 text-sm">
                  {result.generated_layout.size_adjustments.map(
                    (adjustment, index) => (
                      <p key={index}>
                        {adjustment.label}: {renderAdjustmentValue(adjustment)}
                      </p>
                    )
                  )}
                </div>
              </div>
            )}

          <div className="border rounded-xl p-5 bg-gray-50">
            <h2 className="text-xl font-semibold mb-3">Высоты</h2>

            <div className="space-y-1 text-sm">
              <p>
                Рост заказчика:{" "}
                <span className="font-semibold">
                  {String(result.generated_layout.customer_height_cm)} см
                </span>
              </p>

              <p>
                Рекомендованная высота столешницы:{" "}
                <span className="font-semibold">
                  {String(result.generated_layout.countertop_height_mm)} мм
                </span>
              </p>

              <p>
                Цоколь:{" "}
                <span className="font-semibold">
                  {String(result.generated_layout.plinth_height_mm)} мм
                </span>
              </p>

              <p>
                Толщина столешницы:{" "}
                <span className="font-semibold">
                  {String(result.generated_layout.countertop_thickness_mm)} мм
                </span>
              </p>

              <p>
                Высота нижних модулей:{" "}
                <span className="font-semibold">
                  {String(result.generated_layout.base_module_height_mm)} мм
                </span>
              </p>

              <p>
                Формула: высота столешницы = цоколь + толщина столешницы +
                высота нижних модулей
              </p>
            </div>
          </div>

          <div className="border rounded-xl p-5">
            <div className="flex items-center justify-between gap-3 mb-3">
              <h2 className="text-xl font-semibold">Top view</h2>
              <button
                type="button"
                className="px-3 py-2 rounded-lg border text-sm font-semibold"
                onClick={() =>
                  downloadPng("kitchen_top_view.png", result.top_view_svg)
                }
              >
                Скачать PNG
              </button>
            </div>
            <div dangerouslySetInnerHTML={{ __html: result.top_view_svg }} />
          </div>

          <div className="border rounded-xl p-5">
            <div className="flex items-center justify-between gap-3 mb-3">
              <h2 className="text-xl font-semibold">Front view</h2>
              <button
                type="button"
                className="px-3 py-2 rounded-lg border text-sm font-semibold"
                onClick={() =>
                  downloadPng("kitchen_front_view.png", result.front_view_svg)
                }
              >
                Скачать PNG
              </button>
            </div>
            <div dangerouslySetInnerHTML={{ __html: result.front_view_svg }} />
          </div>

          {result.side_view_svg && (
            <div className="border rounded-xl p-5">
              <div className="flex items-center justify-between gap-3 mb-3">
                <h2 className="text-xl font-semibold">Side view</h2>
                <button
                  type="button"
                  className="px-3 py-2 rounded-lg border text-sm font-semibold"
                  onClick={() =>
                    downloadPng("kitchen_side_view.png", result.side_view_svg)
                  }
                >
                  Скачать PNG
                </button>
              </div>
              <div dangerouslySetInnerHTML={{ __html: result.side_view_svg }} />
            </div>
          )}

        </section>
      )}
      </div>
    </main>
  );
}

