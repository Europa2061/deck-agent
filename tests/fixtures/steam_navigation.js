// 在 Steam SharedJSContext 中执行，直接走系统焦点树，不模拟导航算法。
(() => {
  const controller = SteamUIStore.m_GamepadNavigationManager;
  controller.ChangeNavigationSource(1, 0); // ENavigationSourceType.GAMEPAD
  const seen = new Set();
  let nodes = [];
  const walk = node => {
    if (!node || seen.has(node)) return;
    seen.add(node);
    const element = node.m_element;
    if (node.m_Tree.BIsEnabled() && node.m_bMounted !== false && element?.isConnected && element.closest?.('.da-app') && element.getBoundingClientRect().width) nodes.push(node);
    for (const child of node.m_rgChildren || []) walk(child);
  };
  for (const candidate of controller.m_rgAllContexts) {
    for (const tree of candidate.m_rgGamepadNavigationTrees) walk(tree.m_Root);
  }
  const modal = nodes.find(node => node.m_element.closest('.da-modal'))?.m_element.closest('.da-modal');
  nodes = nodes.filter(node => modal ? modal.contains(node.m_element) : node.m_Tree.IsActiveFocusNavTree());
  const find = selector => nodes.filter(node => node.m_element.matches(selector) && !node.m_element.matches(':disabled'));
  const checks = [];
  const original = nodes.find(node => node.BHasFocus());
  const move = (name, from, direction, expected) => {
    if (!from || !expected) return;
    const eventContext = from.m_Tree.WindowContext;
    from.m_Tree.TakeFocus(0);
    from.BTakeFocus(0, direction);
    controller.OnButtonDown(direction, 1, 0, false, from.m_element, eventContext, false);
    controller.OnButtonUp(direction, 1, 0, false, from.m_element, eventContext, false);
    const actual = from.m_Tree.m_lastFocusNode;
    checks.push({ name, pass: typeof expected === 'function' ? Boolean(expected(actual)) : actual === expected });
  };
  try {
    const prompts = find('.da-quick-prompts button');
    move('快捷提示：向右', prompts[0], 12, prompts[1]);
    move('快捷提示：向左', prompts[1], 11, prompts[0]);
    move('快捷提示：向下', prompts[0], 10, prompts[2]);
    move('快捷提示：向上', prompts[2], 9, prompts[0]);
    move('搜索 → 新会话', find('.da-search-button')[0], 12, find('.da-new-session')[0]);
    move('新会话 → 搜索', find('.da-new-session')[0], 11, find('.da-search-button')[0]);
    move('左栏 → 主区域', find('.da-new-session')[0], 12, node => node?.m_element?.closest('.da-main'));
    if (prompts[0]) move('主区域 → 左栏', prompts[0], 11, node => node?.m_element?.closest('.da-rail'));
    const plus = find('.da-composer-plus')[0];
    const editor = find('.da-compose-focus')[0];
    const model = find('.da-model-picker')[0];
    const action = find('.da-composer-action')[0];
    move('加号 → 输入区', plus, 12, editor);
    move('输入区 → 模型', editor, 12, model);
    move('模型 → 语音/任务操作', model, 12, action);
    move('语音/任务操作 → 模型', action, 11, model);
    const voices = find('.da-voice-model-actions button');
    move('语音模型：选择 → 下载/删除', voices[0], 12, voices[1]);
    move('语音模型：下载/删除 → 选择', voices[1], 11, voices[0]);
    return { pass: checks.length > 0 && checks.every(check => check.pass), checks };
  } finally {
    original?.BTakeFocus(0, 0);
  }
})()
