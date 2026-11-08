// Steam 原生深灰主题；按钮颜色与 2px 圆角取自设备上的 DialogButton。
export const styles = `
.da-app{--bg:#23262e;--rail:#1b1d23;--surface:#2d3038;--line:rgba(255,255,255,.12);--text:#dcdedf;--muted:#a7abb1;--blue:#1a9fff;--red:#ffb2b3;--green:#8be0bd;font-family:inherit;display:flex;position:relative;width:100%;height:100%;min-height:0;overflow:hidden;color:var(--text);background:var(--bg);font-size:15px;box-sizing:border-box;text-align:left}
.da-app *{box-sizing:border-box}.da-app h1,.da-app h2,.da-app h3,.da-app p{margin:0}.da-app h1{font-size:25px;letter-spacing:-.03em}.da-app h2{font-size:17px}.da-app h3{font-size:15px}.da-app p{line-height:1.75}.da-app pre{font:12px/1.65 ui-monospace,SFMono-Regular,monospace;white-space:pre-wrap;overflow-wrap:anywhere;padding:12px;background:#1b1d23;border-radius:var(--da-radius);margin:6px 0}.da-app .da-custom-button,.da-app textarea{font:inherit}.da-app button:focus-visible,.da-app textarea:focus-visible,.da-app input:focus-visible{outline:2px solid white;outline-offset:2px}.da-app [data-gpfocus=focus],.da-app .gpfocus{outline:2px solid white!important;outline-offset:2px}.da-app .da-custom-button.da-custom-button{width:auto;max-width:100%;display:flex;align-items:center;justify-content:center;min-height:44px;min-width:44px;padding:8px 12px;font-size:13px;line-height:1.4;cursor:pointer;margin:0;flex-shrink:0}.da-custom-button>span{width:100%;min-width:0}.da-app .da-custom-button:disabled{opacity:.45;cursor:default}.da-app .da-row{display:flex;align-items:center;gap:10px;min-width:0}.da-grow{flex:1;min-width:0}.da-muted{color:var(--muted);font-size:12px}.da-success{color:var(--green);font-size:13px}.da-logo,.da-empty-mark{display:grid;place-items:center;background:#3b3e46;color:white;border-radius:var(--da-radius);width:26px;height:26px;font-size:23px;font-weight:700;transform:rotate(-5deg)}.da-brand{display:flex;align-items:center;gap:8px;padding:0 5px;height:44px;flex-shrink:0}.da-brand strong{font-size:15px}.da-rail{width:192px;display:flex;flex-direction:column;background:var(--rail);border-right:1px solid var(--line);padding:8px;gap:8px;min-height:0;flex-shrink:0}.da-rail.expanded{width:296px}.da-rail>.da-custom-button.new{width:100%}.da-rail-sessions{display:flex;flex-direction:column;min-height:0;flex:1;gap:4px}.da-rail .da-session-heading{margin-top:3px;background:transparent;border:0;color:var(--muted);font-size:12px;justify-content:space-between}.da-session-heading>span{display:flex;justify-content:space-between}.da-session-scroll{display:flex;flex-direction:column;overflow:auto;min-height:0;scrollbar-width:thin}.da-session-scroll>.da-custom-button{text-align:left;justify-content:flex-start}.da-session-name{display:flex;align-items:center;gap:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:13px}.da-session-name>i,.da-status>i{width:6px;height:6px;background:#8c9caf;border-radius:50%;flex-shrink:0}.da-session-name>i.running,.da-status.running>i{background:#1a9fff}.da-session-name>i.waiting,.da-status.waiting>i{background:#ffd08b}.da-status{display:flex;align-items:center;gap:7px;font-size:12px;white-space:nowrap;color:var(--muted)}.da-filters{display:flex;gap:2px}.da-app .da-filters .da-custom-button{flex:1;min-width:0;padding:5px 3px;font-size:12px}.da-app .da-filters .selected{background:#3b3e46}.da-rail-bottom{display:flex;flex-direction:column;border-top:1px solid var(--line);padding-top:4px;gap:2px;flex-shrink:0}.da-rail-bottom .da-custom-button{text-align:left;justify-content:flex-start}.da-main{position:relative;display:flex;flex-direction:column;flex:1;min-width:0;min-height:0}.da-chat-head{height:54px;display:flex;align-items:center;gap:12px;padding:0 18px;border-bottom:1px solid var(--line);flex-shrink:0}.da-chat-head h2{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.da-cwd{font-size:11px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.da-chat-content{flex:1;min-height:0;overflow:auto;padding:14px 18px 8px;scrollbar-width:thin}.da-message{margin-bottom:12px;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.75}.da-message.user{margin-left:auto;max-width:88%;padding:9px 13px;background:#2d3038;border-radius:var(--da-radius);width:fit-content}.da-message.assistant{display:flex;gap:9px}.da-avatar{display:grid;place-items:center;border-radius:var(--da-radius);width:26px;height:26px;background:#3b3e46;color:var(--text);font-size:20px;font-weight:700;flex-shrink:0}.da-message-body{min-width:0;flex:1}.da-message-body p:empty{display:none}.da-tool{margin:0 0 5px 35px;border-bottom:1px solid var(--line)}.da-tool>.da-custom-button{width:100%}.da-tool-title{display:flex;gap:12px;align-items:center;text-align:left}.da-tool-title code{font-size:10px;background:#2d3038;padding:3px 6px;border-radius:var(--da-radius)}.da-tool-title>span:last-child{margin-left:auto}.da-tool-call{font-size:12px;color:var(--muted);margin:5px 0}.da-tool-call summary{cursor:pointer;padding:7px 0;min-height:38px}.da-composer-wrap{padding:6px 16px 12px;flex-shrink:0}.da-composer{display:flex;align-items:center;gap:6px;background:#2d3038;border:1px solid var(--line);border-radius:var(--da-radius);padding:4px 6px 4px 0}.da-composer:focus-within{border-color:var(--line)}.da-compose-focus{min-width:0;flex:1}.da-app .da-composer textarea{display:block;width:100%;height:54px;min-height:54px;resize:none;border:0;color:var(--text);background:transparent;padding:13px 12px;font-size:14px;line-height:1.7;border-radius:var(--da-radius)}.da-app .da-composer textarea:focus{height:82px}.da-composer-actions{display:flex;align-items:center;gap:1px;flex-shrink:0}.da-composer-actions .da-custom-button{padding:6px 9px}.da-app .da-composer-actions .primary{background:#3b3e46}.da-model-picker{max-width:160px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;font-size:12px!important}.da-model-picker>span{overflow:hidden;text-overflow:ellipsis}.da-empty{display:flex;align-items:center;justify-content:center;flex-direction:column;gap:18px;min-height:300px;height:100%;padding:24px}.da-empty-mark{width:48px;height:48px;border-radius:var(--da-radius);font-size:36px}.da-quick-prompts{display:grid;grid-template-columns:1fr 1fr;gap:8px;max-width:560px}.da-quick-prompts .da-custom-button{text-align:left;min-height:48px}.da-working{font-size:12px;color:var(--muted);margin:8px 0 0 35px}.da-settings-head{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:8px 18px;border-bottom:1px solid var(--line);min-height:60px;flex-shrink:0}.da-tabs{display:flex;padding:3px;gap:2px;border-radius:var(--da-radius);background:#23262e}.da-app .da-tabs .selected{background:#2d3038}.da-page-content{padding:12px 18px 18px;overflow:auto;flex:1;min-height:0}.da-provider-list{display:flex;flex-direction:column;gap:8px}.da-provider-card{display:flex;align-items:center;gap:12px;padding:12px 14px;min-height:78px;border:1px solid var(--line);border-radius:var(--da-radius);background:#23262e}.da-provider-card p{color:var(--muted);font-size:12px;margin-top:4px}.da-provider-card h3{display:flex;align-items:center;gap:10px}.da-provider-letter{display:grid;place-items:center;width:34px;height:34px;border-radius:var(--da-radius);background:#3b3e46;font-weight:600;flex-shrink:0}.da-badge{display:inline-flex;font-size:11px;font-weight:500;padding:3px 8px;border-radius:var(--da-radius);background:#3b3e46;color:var(--text)}.da-form{display:flex;flex-direction:column;gap:12px;min-width:0}.da-field{display:flex;flex-direction:column;gap:5px;min-width:0;font-size:13px}.da-field>span{font-weight:550}.da-field input{min-width:0;width:100%;min-height:44px;padding:10px 12px;border:1px solid var(--line);border-radius:var(--da-radius);background:#1b1d23;color:var(--text);font-size:14px}.da-field>div{min-width:0}.da-field-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px;margin:14px 0}.da-setting{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:6px 0;border-bottom:1px solid var(--line);min-height:56px}.da-secret{display:flex;gap:8px;align-items:flex-end}.da-secret>.da-field{flex:1}.da-provider-choices{display:flex;flex-direction:column;gap:4px;max-height:310px;overflow:auto}.da-provider-choices>.da-custom-button{text-align:left}.da-model-card{padding:14px;border:1px solid var(--line);border-radius:var(--da-radius);background:#23262e}.da-model-card p{font-size:12px;color:var(--muted);margin-top:4px}.da-model-card progress{width:100%;height:6px;accent-color:var(--blue);margin:14px 0}.da-model-card>.da-row{flex-wrap:wrap}.da-update-panel{display:flex;align-items:center;gap:12px;padding:14px;background:#23262e;border:1px solid var(--line);border-radius:var(--da-radius)}.da-update-panel h1{font-size:27px;margin:4px 0}.da-update-panel p{font-size:13px}.da-release-notes{max-height:330px;overflow:auto}.da-backdrop{position:absolute;inset:0;z-index:500;display:flex;align-items:center;justify-content:center;padding:24px;background:rgba(255,255,255,0.147);backdrop-filter:blur(3px)}.da-modal{display:flex;flex-direction:column;min-height:0;flex:0 1 auto;max-height:100%;width:560px;max-width:100%;background:#2d3038;border:1px solid var(--line);border-radius:var(--da-radius);box-shadow:0 22px 70px #0008;overflow:hidden}.da-modal-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 16px 8px;flex-shrink:0}.da-modal-head h2{flex:1;min-width:0;overflow-wrap:anywhere}.da-app .da-modal-head>.da-custom-button{width:44px;min-width:44px;max-width:44px;height:44px;padding:0;font-size:22px}.da-modal-body{overflow:auto;min-height:0;padding:0 16px 16px;line-height:1.7;font-size:14px}.da-modal-actions{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px;padding:8px 16px;background:#23262e;border-top:1px solid var(--line);flex-shrink:0}.da-error{color:var(--red);font-size:13px;line-height:1.6;background:#482c3444;border:1px solid #9f687066;border-radius:var(--da-radius);padding:10px 12px;white-space:pre-wrap;overflow-wrap:anywhere;margin:4px 0;flex-shrink:0}.da-context,.da-pending{display:flex;justify-content:space-between;align-items:center;padding:8px 18px;background:#2d3038;gap:12px;font-size:13px}.da-pending{position:absolute;top:54px;left:0;right:0}.da-editor{width:100%;height:180px;background:#1b1d23;color:var(--text);border:1px solid var(--line);border-radius:var(--da-radius);padding:12px}.da-command-description{display:block;font-size:12px;color:var(--muted);margin-top:4px}.da-recording{padding:24px;text-align:center}.da-recording>span{font-size:44px;color:#ffb2b3}.da-recording h1{font-size:32px;margin-top:18px}.da-check{display:flex;align-items:center;gap:8px;font-size:13px}.da-qam{padding:12px;overflow:auto;width:100%}.da-compact{min-height:250px;height:auto;max-height:calc(100vh - 150px);font-size:14px}.da-qam>.da-row{flex-wrap:wrap}.da-qam-current{padding:10px 12px;border:1px solid var(--line);border-radius:var(--da-radius);margin:12px 0}.da-qam-current p{font-size:11px;color:var(--muted);margin-top:4px}.da-compact .da-composer-wrap{padding:0;margin:10px 0 12px}.da-compact .da-composer{display:block;padding:0 5px 6px}.da-compact .da-composer-actions{flex-wrap:wrap;justify-content:space-between}.da-compact .da-model-picker{max-width:120px}.da-qam-tasks{display:flex;flex-direction:column;margin-top:12px;gap:2px}.da-qam-tasks .da-custom-button{width:100%}.da-task-title{display:flex;align-items:center;justify-content:space-between;gap:12px;text-align:left}.da-compact .da-backdrop{position:fixed;top:var(--basicui-header-height,40px);bottom:var(--basicui-footer-height,48px)}
/* 弹层直接限制在遮罩内，不能依赖 Steam 原生弹窗的中间包装层传递高度。 */
.da-app .da-modal{display:grid;grid-template-rows:auto minmax(0,1fr);height:auto;min-height:0;max-height:100%;width:560px;max-width:100%;margin:0}
.da-app .da-modal-with-actions{grid-template-rows:auto minmax(0,1fr) auto}
.da-app .da-modal-body{overflow-y:auto;overflow-x:hidden;min-height:0;overscroll-behavior:contain;touch-action:pan-y;scroll-padding:12px;scrollbar-width:thin}
.da-app .da-modal-head,.da-app .da-modal-actions{min-width:0;position:relative;z-index:1}
.da-app .da-inline-fields{margin:0}.da-extension-status{font-size:12px;color:var(--muted);padding:2px 18px}
/* 紧凑布局：优先节省纵向空间，保留清晰的焦点边框。 */
.da-app{font-size:13px}
.da-app h1{font-size:22px}.da-app h2{font-size:15px}.da-app h3{font-size:13px}.da-app p{line-height:1.55}
.da-app .da-custom-button.da-custom-button{min-height:36px;min-width:36px;padding:6px 10px;font-size:12px;line-height:1.35}
.da-app .da-modal-head>.da-custom-button{width:36px;min-width:36px;max-width:36px;height:36px;padding:0;font-size:20px}
.da-app .da-backdrop{padding:16px}
.da-app .da-modal-head{padding:6px 12px;gap:8px}
.da-app .da-modal-body{padding:0 12px 12px;font-size:13px;line-height:1.55}
.da-app .da-modal-actions{padding:6px 12px;gap:6px}
.da-app .da-form{gap:8px}.da-app .da-field{font-size:12px;gap:4px}
.da-app .da-field input,.da-app .da-field select{min-height:36px;height:36px;padding:6px 10px;font-size:13px}
.da-app .da-select button,.da-app .da-select [role="button"]{min-height:36px;padding:6px 10px;font-size:13px;line-height:1.35;box-sizing:border-box}
.da-app .da-field-grid{gap:8px;margin:8px 0}.da-app .da-inline-fields{margin:0}
.da-app .da-secret{gap:6px}.da-app .da-row{gap:8px}
.da-app .da-chat-head{height:44px;padding:0 12px;gap:8px}
.da-app .da-settings-head{min-height:46px;padding:4px 12px;gap:8px}
.da-app .da-page-content{padding:10px 12px 12px}
.da-app .da-chat-content{padding:10px 12px 6px}
.da-app .da-message{margin-bottom:8px;line-height:1.55}
.da-app .da-message.user{padding:7px 10px}
.da-app .da-composer-wrap{padding:4px 12px 8px}
.da-app .da-composer textarea{height:42px;min-height:42px;padding:9px 10px;font-size:13px;line-height:1.5}
.da-app .da-composer textarea:focus{height:64px}
.da-app .da-brand{height:36px}.da-app .da-brand strong{font-size:12px!important;white-space:nowrap;flex-shrink:0;letter-spacing:-.02em}
.da-app .da-rail{gap:6px;padding:6px;width:180px}.da-app .da-rail.expanded{width:270px}
.da-app .da-session-name{font-size:12px;gap:7px}
.da-app .da-provider-card{min-height:62px;padding:8px 10px;gap:8px}
.da-app .da-provider-letter{width:30px;height:30px}
.da-app .da-setting{min-height:44px;padding:4px 0;gap:10px}
.da-app .da-model-card,.da-app .da-update-panel{padding:10px}
.da-app .da-empty{min-height:180px;padding:16px;gap:12px}
.da-app .da-quick-prompts .da-custom-button{min-height:38px}
.da-app .da-error{padding:7px 9px;font-size:12px}
.da-app .da-pending{top:44px}.da-app .da-context,.da-app .da-pending{padding:6px 12px;font-size:12px}
.da-app .da-qam{padding:8px}.da-app .da-qam-current{padding:8px 10px;margin:8px 0}
.da-app .da-editor{height:140px;font:13px/1.5 ui-monospace,monospace}

/* Steam 的 DialogButton 含高优先级样式；只在插件控件内接管外观。 */
.da-app .da-custom-button.da-custom-button{font-family:inherit!important;font-size:12px!important;font-weight:500!important;line-height:1.35!important;min-height:32px!important;min-width:32px!important;padding:6px 10px!important;letter-spacing:normal!important}
.da-app .da-custom-button.da-custom-button:disabled,.da-app .da-custom-button.da-custom-button.Disabled{opacity:.4!important;cursor:default}
.da-app{--bg:#23262e;--rail:#1b1d23;--muted:#a7abb1;--text:#dcdedf}
.da-app .da-rail{width:164px;padding:8px;gap:7px;border-color:var(--line)}
.da-app .da-rail.expanded{width:220px}
.da-app .da-brand{height:32px;padding:0 4px;gap:8px}.da-app .da-brand strong{font-size:12px!important;white-space:nowrap;flex-shrink:0;letter-spacing:-.02em}
.da-app .da-logo{width:23px;height:23px;font-size:21px;background:#3b3e46;transform:none;border-radius:var(--da-radius)}
.da-app .da-rail>.da-custom-button.new{text-align:left}
.da-app .da-rail .da-session-heading{background:transparent!important;border-color:transparent!important;color:var(--muted)!important;font-size:11px!important;min-height:28px!important}
.da-app .da-session-scroll{gap:3px}
.da-app .da-session-scroll>.da-custom-button{padding:7px 9px!important;text-align:left}
.da-app .da-rail-bottom{gap:3px;padding-top:7px}.da-app .da-rail-bottom .da-custom-button{font-size:11px!important}
.da-app .da-chat-head{height:40px;padding:0 16px;border-color:var(--line);background:#23262e}
.da-app .da-chat-head h2{font-size:14px;font-weight:600;letter-spacing:0}
.da-app .da-chat-content{padding:18px 22px 10px;scrollbar-color:#23262e transparent}
.da-app .da-message{margin-bottom:18px;line-height:1.65}
.da-app .da-message.assistant{gap:10px}
.da-app .da-message-body{font-size:13px}
.da-app .da-avatar{width:23px;height:23px;font-size:19px;border-radius:var(--da-radius);background:#2d3038;color:var(--text);margin-top:1px}
.da-app .da-message.user{background:#2d3038;border:1px solid var(--line);padding:8px 12px;border-radius:var(--da-radius);max-width:85%}
.da-app .da-message.user p{white-space:pre-wrap}
.da-app .da-tool{margin-left:33px;border-color:var(--line)}
.da-app .da-tool>.da-custom-button{font-size:11px!important;padding:5px 0!important;min-height:28px!important}
.da-app .da-tool-call>.da-custom-button{font-size:11px!important}
.da-app .da-composer-wrap{padding:5px 14px 10px}
.da-app .da-composer{border:1px solid var(--line);background:#23262e;border-radius:var(--da-radius);padding:4px 5px 4px 0;gap:5px}
.da-app .da-composer:focus-within{border-color:var(--line);box-shadow:0 0 0 1px rgba(255,255,255,0.027)}
.da-app .da-composer textarea{height:38px;min-height:38px;font-size:13px;padding:8px 10px;line-height:1.6}
.da-app .da-composer textarea:focus{height:60px}
.da-app .da-composer textarea::placeholder{color:var(--muted)}
.da-app .da-composer-actions{gap:3px}
.da-app .da-composer-actions .da-custom-button{padding:5px 7px!important;min-height:30px!important}
.da-app .da-composer-actions .da-custom-button.da-model-picker{max-width:132px;font-size:11px!important}
.da-app .da-icon-button>span{display:flex;align-items:center;justify-content:center}
.da-app .da-pending{top:40px}
.da-app .da-modal{border-color:var(--line);border-radius:var(--da-radius);background:#23262e}
.da-app .da-modal-head{padding:8px 12px;border-bottom:1px solid var(--line);margin-bottom:10px}
.da-app .da-modal-head>.da-custom-button{width:32px!important;height:32px!important;max-width:32px!important;min-width:32px!important;padding:0!important;font-size:19px!important}
.da-app .da-modal-actions{background:#23262e;padding:8px 12px;border-color:var(--line)}
.da-app .da-field input,.da-app .da-field select{height:34px;min-height:34px;font-size:12px;border-radius:var(--da-radius)}
.da-app .da-select button,.da-app .da-select [role="button"]{font-size:12px!important;min-height:34px!important;border-radius:var(--da-radius)!important}
.da-app .da-markdown{white-space:normal;overflow-wrap:anywhere;line-height:1.65;color:var(--text)}
.da-app .da-markdown>:first-child{margin-top:0}.da-app .da-markdown>:last-child{margin-bottom:0}
.da-app .da-markdown p{margin:0 0 10px;line-height:1.65}
.da-app .da-markdown h1,.da-app .da-markdown h2,.da-app .da-markdown h3,.da-app .da-markdown h4{margin:16px 0 7px;font-weight:650;line-height:1.45;letter-spacing:0;color:var(--text)}
.da-app .da-markdown h1{font-size:19px}.da-app .da-markdown h2{font-size:16px}.da-app .da-markdown h3{font-size:14px}.da-app .da-markdown h4,.da-app .da-markdown h5,.da-app .da-markdown h6{font-size:13px}
.da-app .da-markdown strong{font-weight:650;color:var(--text)}
.da-app .da-markdown ul,.da-app .da-markdown ol{margin:6px 0 12px;padding-left:22px}
.da-app .da-markdown li{margin:4px 0;padding-left:2px}.da-app .da-markdown li>p{margin:0 0 5px}
.da-app .da-markdown li::marker{color:var(--muted)}
.da-app .da-markdown blockquote{border-left:3px solid var(--line);margin:10px 0;padding:6px 12px;background:rgba(255,255,255,0.053);color:var(--muted)}
.da-app .da-markdown a{color:var(--muted);text-decoration:underline;text-underline-offset:3px;cursor:pointer}
.da-app .da-markdown :not(pre)>code{font:11px/1.5 ui-monospace,SFMono-Regular,monospace;color:var(--text);background:#2d3038;border:1px solid var(--line);padding:1px 5px;border-radius:var(--da-radius);white-space:break-spaces;overflow-wrap:anywhere}
.da-app .da-code-block{margin:10px 0;border:1px solid var(--line);border-radius:var(--da-radius);overflow:hidden;background:#1b1d23}
.da-app .da-code-head{display:flex;align-items:center;justify-content:space-between;padding:3px 9px;background:#2d3038;border-bottom:1px solid var(--line);font:10px/1.5 ui-monospace,monospace;color:var(--muted)}
.da-app .da-code-head .da-custom-button{min-height:24px!important;min-width:0!important;padding:3px 7px!important;font-size:10px!important}
.da-app .da-markdown pre{margin:0;background:transparent;padding:10px 12px;overflow-x:auto;white-space:pre;font:11px/1.65 ui-monospace,SFMono-Regular,monospace;scrollbar-width:thin}
.da-app .da-table-scroll{overflow-x:auto;max-width:100%;margin:10px 0 14px;border:1px solid var(--line);border-radius:var(--da-radius);scrollbar-width:thin}
.da-app .da-markdown table{border-collapse:collapse;min-width:100%;font-size:12px}
.da-app .da-markdown th,.da-app .da-markdown td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:left;white-space:normal;min-width:76px}
.da-app .da-markdown th{background:#2d3038;color:var(--text);font-weight:600}
.da-app .da-markdown tr:last-child td{border-bottom:0}
.da-app .da-markdown hr{border:0;border-top:1px solid var(--line);margin:16px 0}
.da-app .da-markdown .contains-task-list{list-style:none;padding-left:0}
.da-app .da-markdown input[type="checkbox"]{accent-color:var(--muted);margin-right:7px}
.da-app .da-compact .da-chat-content{padding:10px}
@media(max-width:900px){.da-app .da-chat-content{padding:14px 16px 8px}.da-app .da-rail{width:152px}.da-app .da-rail.expanded{width:194px}.da-app .da-composer-wrap{padding-left:10px;padding-right:10px}.da-app .da-composer-actions .da-model-picker{max-width:112px}}
.da-app.da-compact .da-composer-wrap{padding:0;margin:8px 0}.da-app.da-compact .da-composer-actions{flex-wrap:wrap;justify-content:space-between}

.da-app .da-enabled-model{display:flex;align-items:center;gap:6px;border-bottom:1px solid var(--line);padding:6px 0;min-width:0}
.da-app .da-enabled-model .da-grow{min-width:0;overflow-wrap:anywhere}
.da-app .da-enabled-model small{display:block;color:var(--muted);font-size:10px}
.da-app .da-provider-models{display:flex;flex-direction:column;gap:8px}
.da-app .da-model-add-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px}
.da-app .da-model-add-list .da-custom-button{min-width:0!important;overflow-wrap:anywhere}
.da-app .da-provider-card .da-provider-open{padding:0!important;border:0!important;background:transparent!important;text-align:left;justify-content:flex-start}
.da-app .da-voice-settings{display:flex;flex-direction:column;gap:20px}
.da-app .da-voice-section{display:flex;flex-direction:column;gap:10px;min-width:0}
.da-app .da-voice-section+.da-voice-section{border-top:1px solid var(--line);padding-top:16px}
.da-app .da-voice-section-head{display:flex;flex-direction:column;gap:3px}
.da-app .da-voice-section-head h2{font-size:15px;color:var(--text)}
.da-app .da-voice-section-head p{line-height:1.55}
.da-app .da-voice-section .da-field-grid{margin:0}
.da-app .da-microphone-settings{display:flex;flex-direction:column;gap:5px;min-width:0}
.da-app .da-microphone-settings .da-row{align-items:flex-end}
.da-app .da-voice-section>.da-custom-button{align-self:flex-start}
.da-app .da-voice-models{display:flex;flex-direction:column;gap:6px}
.da-app .da-voice-model{min-width:0;padding:10px 12px;border:1px solid var(--line);border-radius:var(--da-radius);background:#23262e}
.da-app .da-voice-model.selected{background:#2d3038;border-color:var(--line)}
.da-app .da-voice-model-top{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;min-width:0}
.da-app .da-voice-model-top strong{flex:1 1 150px;min-width:0;font-size:13px;overflow-wrap:anywhere}
.da-app .da-voice-model-actions{display:flex;gap:5px;flex-wrap:wrap}
.da-app .da-voice-model-actions .da-custom-button.da-custom-button{min-height:30px!important;padding:4px 8px!important}
.da-app .da-voice-download-progress{margin-top:8px}
.da-app .da-voice-download-progress progress{width:100%;height:6px;accent-color:var(--blue)}
.da-app .da-voice-model-description{display:block;margin-top:5px;color:var(--muted);font-size:12px;line-height:1.45}
.da-app .da-voice-model-meta{display:flex;align-items:center;flex-wrap:wrap;gap:5px 8px;margin-top:8px;color:var(--muted);font-size:11px}
.da-app .da-voice-model-tag{padding:2px 6px;border:1px solid var(--line);border-radius:var(--da-radius);line-height:1.3}
.da-app .da-voice-model-tag.installed{color:#a4dfc3;border-color:#41745f;background:#203d35}
/* 直接输入：左侧功能菜单，右侧语音/发送共享同一个圆形位置。 */
.da-app .da-composer{display:flex!important;align-items:flex-end;padding:5px 6px;gap:6px;border-radius:var(--da-radius)}
.da-app .da-compose-focus{flex:1;min-width:0;align-self:center}
.da-app .da-composer textarea,.da-app .da-composer textarea:focus{display:block;height:auto;min-height:38px;max-height:144px;padding:8px 5px;resize:none;overflow-x:hidden;overflow-y:auto;scrollbar-width:none;line-height:1.6;transition:none}
.da-app .da-composer textarea::-webkit-scrollbar{display:none}
.da-app .da-composer-actions{align-items:center;align-self:flex-end;gap:5px;min-height:38px;flex-wrap:nowrap!important}
.da-app .da-composer-more{position:relative;align-self:flex-end;display:flex;align-items:center;min-height:38px}
.da-app .da-custom-button.da-composer-plus{width:32px!important;height:32px!important;min-width:32px!important;padding:0!important}
.da-app .da-composer-menu{position:absolute;bottom:calc(100% + 10px);left:0;width:320px;max-height:min(360px,calc(100dvh - 180px));overflow-y:auto;overscroll-behavior:contain;scrollbar-width:thin;padding:6px;border:1px solid var(--line);border-radius:var(--da-radius);background:#23262e;box-shadow:0 10px 30px #0007;z-index:510}
.da-app .da-composer-menu .da-custom-button{width:100%!important;text-align:left!important}
.da-app .da-composer-menu .da-custom-button>span{display:block;min-width:0}
.da-app .da-composer-command-groups section+section,.da-app .da-composer-command-footer{border-top:1px solid var(--line);margin-top:5px;padding-top:5px}
.da-app .da-composer-command-groups h3{padding:5px 8px;font-size:11px;color:var(--muted);font-weight:600}
.da-app .da-composer-command-groups p{padding:5px 8px}
.da-app .da-composer-menu .da-command-description{font-size:11px;line-height:1.5;margin-top:2px;white-space:normal;overflow-wrap:anywhere}
.da-app .da-composer-actions .da-custom-button.da-composer-action{width:32px!important;height:32px!important;min-width:32px!important;min-height:32px!important;max-width:32px!important;flex:0 0 32px;padding:0!important}
.da-app .da-composer-actions .da-custom-button.da-submit-action{width:27.2px!important;height:27.2px!important;min-width:27.2px!important;min-height:27.2px!important;max-width:27.2px!important;flex-basis:27.2px}
.da-app .da-composer-actions .da-custom-button.da-model-picker{align-self:center;min-height:28px!important;padding:3px 6px!important;max-width:122px}
.da-app.da-compact .da-composer{display:flex!important;padding:5px;gap:4px}
.da-app.da-compact .da-composer-actions{justify-content:flex-end;gap:2px}
.da-app.da-compact .da-composer-actions .da-custom-button.da-model-picker{max-width:82px}
.da-app .da-qam{min-height:0}

.da-app .da-composer textarea:focus-visible,.da-app .da-compose-focus.gpfocus,.da-app .da-compose-focus[data-gpfocus="focus"]{outline:none!important;outline-offset:0!important;box-shadow:none!important}
.da-app .da-composer:focus-within{border-color:var(--line);box-shadow:0 0 0 1px rgba(255,255,255,0.053)}

.da-app .da-rail-actions{display:flex;align-items:center;gap:6px;width:100%}
.da-app .da-rail-actions .da-search-button{width:32px!important;height:32px!important;min-width:32px!important;padding:0!important;flex:0 0 32px;border-radius:var(--da-radius)!important;background:#2d3038!important;border-color:var(--line)!important}
.da-app .da-rail-actions .da-new-session{flex:1;min-width:0!important;background:#2d3038!important;border-color:var(--line)!important;text-align:left}
.da-app .da-session-label{font-size:11px;color:var(--muted);padding:10px 8px 6px}
.da-app .da-session-dot{display:inline-block;position:relative;width:10px;height:10px;flex:0 0 10px}
.da-app .da-session-dot::before{content:"";position:absolute;inset:2px;border-radius:50%;background:#8497aa}
.da-app .da-session-dot.unread::before{background:#32adff}
.da-app .da-session-dot.busy::before{inset:0;background:transparent;border:1.5px solid #3c5870;border-top-color:#78caff;animation:da-session-spin .8s linear infinite}
@keyframes da-session-spin{to{transform:rotate(360deg)}}
.da-app .da-search-results{display:flex;flex-direction:column;gap:5px}
.da-app .da-search-results>.da-custom-button{text-align:left}
.da-app .da-search-session{display:flex;flex-direction:column;gap:3px;min-width:0;flex:1}
.da-app .da-search-session strong{font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.da-app .da-search-session small{font-size:10px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.da-app .da-settings-head{align-items:center;flex-wrap:wrap;padding:0 12px;gap:0 12px}
.da-app .da-select-trigger.da-custom-button{width:100%!important;min-width:0!important;text-align:left}
.da-select-trigger-content,.da-select-option-content{display:flex;align-items:center;justify-content:space-between;gap:10px;min-width:0;width:100%}
.da-select-trigger-content>span:first-child{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.da-select-chevron{font-size:16px;line-height:1;color:var(--muted);flex-shrink:0}
.da-app .da-modal{position:relative}
.da-app .da-modal.da-select-menu-open{overflow:visible}
.da-app .da-select-popover{position:absolute;z-index:650;overflow-y:auto;overscroll-behavior:contain;padding:5px;background:#23262e;border:1px solid var(--line);border-radius:var(--da-radius);box-shadow:0 12px 30px rgba(255,255,255,0.147),0 2px 6px rgba(255,255,255,0.120);scrollbar-width:thin}
.da-app .da-select-popover .da-select-option.da-custom-button{width:100%!important;min-width:0!important;min-height:34px!important;padding:7px 9px!important;text-align:left}
.da-app .da-settings-head .da-tabs{display:flex;flex:1 1 320px;flex-wrap:wrap;gap:0 4px;min-width:0;padding:0;background:transparent;border-radius:var(--da-radius)}
.da-app .da-settings-head .da-tabs .da-custom-button.da-custom-button{position:relative;min-height:46px!important;padding:10px 10px!important;white-space:nowrap}
.da-app .da-settings-head .da-tabs .da-custom-button.da-custom-button.selected{font-weight:600!important}
.da-app .da-settings-head .da-tabs .da-custom-button.da-custom-button.selected::after{content:"";position:absolute;left:10px;right:10px;bottom:0;height:3px}
.da-app .da-settings-head>.da-custom-button{margin:5px 0!important}
.da-app .da-error-banner{display:flex;align-items:center;gap:4px;min-width:0;padding:3px 9px}
.da-error-message{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.da-app .da-error-banner .da-custom-button{min-height:26px!important;padding:3px 8px!important}
@media(prefers-reduced-motion:reduce){.da-app .da-session-dot.busy::before{animation:none}}

/* Steam 控件保留系统外观；这里只负责插件所需的布局。 */
.da-native-controls{min-width:0;min-height:0}
.da-native-controls .da-native-button{width:100%;margin:0}
.da-button-content{display:flex;align-items:center;justify-content:center;gap:7px;min-width:0}
.da-row>.da-native-button,.da-enabled-model>.da-native-button,.da-voice-model-actions>.da-native-button,.da-modal-actions>.da-native-button{width:auto;flex-shrink:0}
.da-settings{display:flex;flex-direction:column;flex:1;overflow:hidden}
.da-settings-actions{padding:10px 16px 0;display:flex;justify-content:flex-end}
.da-settings-actions .da-native-button{width:auto}
.da-settings .da-provider-list{gap:0}
.da-settings .da-provider-card{border:0;border-bottom:1px solid rgba(255,255,255,0.022);border-radius:var(--da-radius);background:transparent;flex-wrap:wrap;gap:10px;padding:14px 6px}
.da-settings .da-provider-open{flex:1;min-width:180px;text-align:left}
.da-settings .da-provider-card>.da-native-button:not(.da-grow){width:auto}
.da-settings .da-setting{padding:12px 0;min-height:60px}
.da-settings .da-setting>.da-native-button{width:auto;flex-shrink:0}
.da-settings .da-setting>.da-grow{flex:1;min-width:0}
.da-settings .da-provider-card>.da-provider-open{width:auto;min-width:180px;flex:1}
.da-native-field{min-width:0;flex:1}
.da-native-select,.da-native-toggle{min-width:0}
.da-dialog-surface{width:min(560px,calc(100vw - 32px));height:auto;max-height:calc(100dvh - 112px);background:transparent;overflow:visible}
.da-dialog-host{display:flex;width:100%;min-height:0;max-height:calc(100dvh - 112px)}
.da-dialog-host>.da-modal{max-height:calc(100dvh - 112px);width:100%}
.da-modal-head>.da-native-button{width:36px;min-width:36px;max-width:36px;padding:0;flex-shrink:0}
.da-modal-actions{align-items:center}
.da-secret>.da-native-field{flex:1}.da-secret>.da-native-button{width:auto}
.da-composer-command-groups .da-native-button{justify-content:flex-start;text-align:left;margin-bottom:4px}
.da-loading,.da-task-feedback{display:flex;align-items:center;gap:8px;color:var(--text);font-size:13px;line-height:1.5}
.da-loading{padding:12px 0}
.da-spinner{display:inline-block;flex:0 0 15px;width:15px;height:15px;border:2px solid currentColor;border-right-color:transparent;border-radius:50%;animation:da-session-spin .8s linear infinite}
.da-task-feedback{padding:7px 16px;flex-shrink:0;background:#23262e;border-top:1px solid var(--line)}
.da-task-feedback:not(.working){color:var(--text)}
.da-announcement{position:absolute;right:12px;top:48px;max-width:calc(100% - 24px);z-index:450;padding:9px 14px;border-radius:var(--da-radius);background:#244c3f;color:#ddfff1;box-shadow:0 4px 16px #0006;font-size:13px;pointer-events:none}
.da-button-error{color:#ffb2b3;font-size:12px;line-height:1.5;overflow-wrap:anywhere}
.da-app .da-compose-focus.gpfocus,.da-app .da-compose-focus[data-gpfocus="focus"]{outline:3px solid var(--text)!important;outline-offset:3px!important;box-shadow:0 0 0 5px rgba(255,255,255,0.027)!important;border-radius:var(--da-radius)}
.da-app .da-chat-content:focus-visible,.da-app .da-chat-content.gpfocus{outline:2px solid var(--text);outline-offset:-3px}
.da-app .da-composer-actions .da-custom-button.da-composer-action{width:40px!important;height:40px!important;min-width:40px!important;min-height:40px!important;max-width:40px!important;flex-basis:40px;background-clip:padding-box}
.da-composer-action .da-busy-text{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}
.da-app .da-composer-actions .da-custom-button.da-submit-action{position:relative}
.da-app .da-composer-actions .da-custom-button.da-submit-action::before{content:"";position:absolute;width:27.2px;height:27.2px;left:50%;top:50%}
.da-submit-action>.da-button-content{position:relative;z-index:1}
.da-status.sending>i,.da-status.stopping>i{background:#ffd08b}.da-status.completed>i{background:#8be0bd}
.da-message-pending{opacity:.7}.da-message-pending small{display:block;margin-top:5px;font-size:11px}.da-message-pending.failed{border-color:var(--line)!important;color:var(--text)}
.da-latest{display:flex;justify-content:center;flex-shrink:0;padding:4px}
.da-session-dot.attention{display:grid;place-items:center;color:#111923;background:#ffd08b;border-radius:50%;font-size:9px;font-weight:700}
.da-session-dot.attention::before{display:none}.da-session-dot.attention.error,.da-session-dot.attention.interrupted{background:#ffadb6}
.da-qam-current{display:flex;justify-content:space-between;align-items:center;gap:10px}
.da-qam .da-native-button{text-align:left}
.da-qam-feedback{font-size:12px;color:var(--text);line-height:1.5;padding:4px 0}
/* 只约束原生控件的几何，不覆盖它们的颜色、字体和焦点行为。 */
.da-native-modal-root{width:min(560px,calc(100vw - 48px))!important;min-width:0!important;max-width:calc(100vw - 48px)!important;padding:0!important;box-sizing:border-box!important}
.da-native-modal-root>*{min-width:0;max-width:100%;width:100%}
.da-native-modal-root .da-dialog-surface{width:100%;max-width:100%}
.da-dialog-surface,.da-dialog-host,.da-dialog-host>.da-modal{max-height:calc(100dvh - max(40px,var(--basicui-header-height,40px)) - max(48px,var(--basicui-footer-height,48px)) - 48px)}
.da-modal-head>.da-native-button{width:36px!important;min-width:36px!important;max-width:36px!important;height:36px!important;min-height:36px!important;padding:0!important}
.da-secret>.da-native-button{min-width:56px!important;width:auto!important}
.da-enabled-model>.da-native-button{min-width:72px!important;width:auto!important}
.da-session-scroll .da-button-content,.da-rail-bottom .da-button-content{justify-content:flex-start}

/* 浏览器适配层只近似展示原生布局；生产入口不会生成这些类名。 */
.da-app .da-dev-button.da-native-button{padding:9px 13px}
.da-app .da-dev-button.da-native-button:disabled{opacity:.45}

.da-dev-modal-backdrop{position:fixed;inset:0;z-index:900;display:flex;align-items:center;justify-content:center;background:#000b;padding:16px}
.da-app .da-dev-button.da-native-button,.da-app .da-dev-tablist button,.da-app .da-dev-toggle{font-size:15px;line-height:1.4}
.da-dev-modal-backdrop .da-native-button,.da-native-controls .da-native-button{min-height:38px}
.da-app .da-dev-field{display:flex;flex-direction:column;gap:7px;padding:6px 0;font-size:14px;color:var(--text);min-width:0}
.da-app .da-dev-field input,.da-app .da-dev-field select{width:100%;min-width:0;height:38px;padding:6px 10px;background:#1b1d23;color:var(--text);border:1px solid var(--line);border-radius:var(--da-radius);font:inherit}
.da-app .da-native-button{cursor:pointer}
.da-dev-modal-backdrop .da-native-button:not([class*="DialogButton"]),.da-dev-section-row .da-native-button:not([class*="DialogButton"]){padding:8px 12px}
.da-app .da-dev-toggle{display:flex;width:100%;align-items:center;justify-content:space-between;text-align:left;padding:14px 8px;background:transparent;border:0;border-bottom:1px solid rgba(255,255,255,0.025);color:var(--text);gap:14px;cursor:pointer}
.da-dev-toggle small{display:block;font-size:12px;color:var(--muted);margin-top:5px}.da-dev-switch{width:38px;height:22px;flex:0 0 38px;border-radius:20px;background:#3b3e46;padding:3px}.da-dev-switch:after{content:"";display:block;width:16px;height:16px;background:white;border-radius:50%}.da-dev-switch.on{background:#3b3e46}.da-dev-switch.on:after{margin-left:16px}
.da-dev-tabs{display:flex;flex-direction:column;flex:1;min-height:0;overflow:hidden}
.da-dev-tablist{display:flex;flex-shrink:0;border-bottom:1px solid var(--line);gap:4px;padding:0 12px;flex-wrap:wrap}
.da-dev-tablist button{padding:12px 10px;border:0;border-bottom:3px solid transparent;background:transparent;color:var(--muted);cursor:pointer}.da-dev-tablist button[aria-selected=true]{color:white;border-color:var(--line)}
.da-dev-tabpanel{display:flex;flex-direction:column;flex:1;min-height:0;overflow:hidden}
.da-dev-section{padding:8px 0}.da-dev-section h3{font-size:13px;color:var(--muted);padding:4px 0 10px}.da-dev-section-row{margin:4px 0}
.da-app .da-dev-tablist button:focus-visible,.da-app .da-dev-toggle:focus-visible{outline:3px solid var(--text);outline-offset:-3px}

/* 尺寸沿用 Web 版；原生控件继续管理焦点、按键、菜单和交互状态。 */
.da-app{--da-button-height:32px;--da-input-height:34px;--da-control-font:12px;--da-body-font:13px}
.da-app .da-native-button.da-native-button{min-width:32px!important;min-height:var(--da-button-height)!important;height:auto!important;padding:6px 10px!important;font-family:inherit!important;font-size:var(--da-control-font)!important;line-height:1.35!important}
.da-app .da-modal-head>.da-native-button{width:32px!important;min-width:32px!important;max-width:32px!important;height:32px!important;min-height:32px!important;padding:0!important;font-size:19px!important}
.da-app .da-secret>.da-native-button{min-width:44px!important}
.da-app .da-enabled-model>.da-native-button{min-width:0!important}
.da-app .da-native-field{font-size:var(--da-body-font);line-height:1.4}
.da-app .da-native-field .DialogInputLabelGroup{margin:0!important}
.da-app .da-native-field .DialogLabel{font-size:var(--da-control-font)!important;line-height:16px!important;margin:0 0 4px!important}
.da-app .da-native-field .DialogInput_Wrapper{min-height:var(--da-input-height)!important}
.da-app .da-native-field input{height:var(--da-input-height)!important;min-height:var(--da-input-height)!important;padding:6px 10px!important;font-family:inherit!important;font-size:var(--da-control-font)!important;line-height:1.4!important;border-radius:var(--da-radius)!important}
.da-app .da-native-select,.da-app .da-native-toggle{font-size:var(--da-body-font);line-height:1.4}
.da-app .da-native-select *,.da-app .da-native-toggle *{font-size:inherit!important;line-height:inherit!important}
.da-app .da-native-select>div{padding:0!important;margin:0!important;min-height:0!important}
.da-app .da-native-select [role="combobox"],.da-app .da-native-select select{min-height:var(--da-input-height)!important;height:var(--da-input-height)!important;padding:6px 10px!important;font-size:var(--da-control-font)!important;border-radius:var(--da-radius)!important}
.da-app .da-control-label,.da-app .da-native-select .da-control-label,.da-app .da-native-toggle .da-control-label{font-size:var(--da-control-font)!important;line-height:16px!important}
.da-app .da-control-description,.da-app .da-native-toggle .da-control-description{font-size:11px!important;line-height:1.4!important}
.da-app .da-native-select div:has(>.da-control-label),.da-app .da-native-toggle div:has(>.da-control-label){font-size:12px!important;line-height:16px!important}
.da-app .da-native-toggle div:has(>.da-control-description){font-size:11px!important;line-height:1.4!important}
.da-app .da-native-toggle>div{padding:4px 0!important;min-height:44px!important}
.da-app .da-settings .da-setting{min-height:44px;padding:4px 0;gap:10px}
.da-app .da-settings .da-provider-list{gap:8px}
.da-app .da-settings .da-provider-card{min-height:62px;padding:8px 10px;gap:8px}
.da-app .da-settings-actions{padding:8px 12px 0}
.da-app .da-settings [role="tab"]{font-size:12px!important;padding:6px 10px!important;line-height:1.4!important}
.da-app .da-voice-model-actions .da-native-button{min-height:30px!important;padding:4px 8px!important}
.da-app .da-composer-command-groups .da-native-button{padding:6px 8px!important}
.da-app .da-dev-field{gap:4px;padding:0;font-size:12px}
.da-app .da-dev-field input,.da-app .da-dev-field select{height:34px;padding:6px 10px;font-size:12px}
.da-app .da-dev-toggle{padding:4px 0;min-height:44px;font-size:12px}
.da-app .da-dev-tablist button{font-size:12px;padding:10px}
.da-compact-dropdown-menu [role="option"],.da-compact-dropdown-menu [role="menuitem"]{font-size:13px!important;line-height:1.4!important;min-height:32px!important;padding:6px 10px!important}

/* 会话标题单独省略，滚动区域为焦点边框留出空间。 */
.da-app .da-session-scroll{padding:6px;gap:4px;overflow-x:hidden;scroll-padding:6px;overscroll-behavior:contain}
.da-app .da-session-scroll>.da-button{width:100%;max-width:100%;flex-shrink:0;scroll-margin:6px}
.da-app .da-session-scroll .da-button-content,.da-app .da-session-name{width:100%;min-width:0}
.da-app .da-session-title{display:block;min-width:0;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* 快速侧栏沿用宿主背景，只保留发起会话和最近六条会话。 */
.da-app.da-compact{min-height:0;height:auto;max-height:none;overflow:visible;background:transparent}
.da-app .da-qam{padding:8px 12px;display:flex;flex-direction:column;align-self:stretch;gap:16px;overflow:visible}
.da-qam>*{margin:0!important;padding:0!important;flex-shrink:0}
.da-qam>:first-child>div+div{margin-top:8px}
.da-qam-session .da-button-content{width:100%;justify-content:flex-start}
.da-qam-arrow{margin-left:auto;color:var(--muted);font-size:20px;flex-shrink:0}
.da-app .da-qam .da-qam-session{padding:8px 10px!important;min-height:40px!important}
.da-qam-recents{display:flex;flex-direction:column;gap:6px}
.da-qam-session-info{flex:1;min-width:0;display:flex;flex-direction:column;align-items:flex-start;gap:5px}
.da-qam-session-info>.da-status{padding-left:17px;font-size:11px}
.da-qam-empty{padding:8px 0}

/* 供应商信息和操作分开，避免按钮内部的横向布局挤压文字。 */
.da-app .da-settings .da-provider-card{display:grid;grid-template-columns:30px minmax(0,1fr) auto;align-items:start;gap:12px;padding:14px 0;min-height:76px}
.da-provider-info{min-width:0;display:flex;flex-direction:column;gap:4px}
.da-provider-title{display:flex;align-items:center;flex-wrap:wrap;gap:8px;min-width:0}
.da-provider-title h3{min-width:0;overflow-wrap:anywhere;line-height:1.5}
.da-app .da-provider-info p{margin:0;line-height:1.5}
.da-provider-model{overflow-wrap:anywhere}
.da-provider-actions{display:flex;align-items:center;justify-content:flex-end;flex-wrap:wrap;gap:6px;max-width:180px}
.da-app .da-provider-actions>.da-native-button{width:auto}
.da-voice-input-fields{display:flex;flex-direction:column;gap:18px}
.da-microphone-settings{min-width:0;display:flex;flex-direction:column;gap:5px}

/* 构建信息按字段分行，长编号与更新说明允许自然换行。 */
.da-update-info{flex:1;min-width:0;overflow-wrap:anywhere;white-space:normal}
.da-update-actions{display:flex;flex-direction:column;gap:8px;flex-shrink:0}
.da-build-details{margin:8px 0 10px;display:flex;flex-direction:column;gap:6px;font-size:12px;line-height:1.6}
.da-build-details>div{display:grid;grid-template-columns:52px minmax(0,1fr);gap:8px}
.da-build-details dt{color:var(--muted)}.da-build-details dd{margin:0;min-width:0;overflow-wrap:anywhere;white-space:normal}
.da-app .da-update-panel{align-items:flex-start;flex-wrap:wrap}
.da-app .da-updates .da-native-field,.da-app .da-updates .da-native-toggle{flex:none}
.da-app .da-updates p,.da-app .da-release-notes{white-space:pre-wrap;overflow-wrap:anywhere;word-break:normal}
@media(max-width:650px){.da-app .da-settings .da-provider-card{grid-template-columns:30px minmax(0,1fr)}.da-provider-actions{grid-column:2;max-width:none;justify-content:flex-start}.da-update-info{flex-basis:100%}.da-update-actions{flex-direction:row;flex-wrap:wrap}}

@media(prefers-reduced-motion:reduce){.da-spinner{animation:none}}


/* 和 Steam DialogButton 保持相同的普通、悬停、聚焦与按下状态。 */
.da-app{--da-radius:2px;color-scheme:dark}
.da-app .da-button.da-button{color:var(--text)!important;background:rgba(255,255,255,.15)!important;border:0!important;border-radius:var(--da-radius)!important;box-shadow:none!important;text-shadow:none!important;filter:none;transform:none;outline:none;transition:background-color 150ms ease-in}
.da-app .da-button.da-button:enabled:hover{background:rgba(255,255,255,.2)!important}
.da-app .da-button.da-button.selected,.da-app .da-button.da-button.active{background:rgba(255,255,255,.25)!important}
.da-app .da-button.da-button:enabled:is(:focus-visible,:active,.gpfocus,[data-gpfocus="focus"]){background:#fff!important;color:#23262e!important;outline:none!important;box-shadow:0 4px 4px #0004!important;transform:none;filter:none;transition:none}
.da-app .da-button.da-button:enabled:is(:focus-visible,:active,.gpfocus,[data-gpfocus="focus"]) :is(.da-muted,.da-command-description,.da-status,.da-qam-arrow,small){color:inherit!important}
.da-app .da-button.da-button:disabled{background:#131418!important;color:#fff!important;opacity:.4!important;cursor:default}
.da-app .da-composer-actions .da-submit-action::before{display:none}
.da-app .da-logo,.da-app .da-empty-mark,.da-app .da-avatar{background:var(--surface);color:var(--text);transform:none}
.da-app .da-composer:focus-within{border-color:#fff;box-shadow:none}
.da-app .da-compose-focus:is(.gpfocus,[data-gpfocus="focus"]){outline:none!important;box-shadow:none!important}
.da-app :is(input,textarea):focus-visible{outline:2px solid #fff;outline-offset:1px}
.da-app .da-chat-content:is(:focus-visible,.gpfocus){outline:2px solid #fff;outline-offset:-2px}
.da-app .da-new-session svg,.da-app .da-qam-create svg{flex-shrink:0}
.da-app .da-qam .da-qam-create{min-height:40px!important;padding:9px 12px!important;font-size:14px!important}
.da-app .da-qam .da-qam-session{height:32px!important;min-height:32px!important;padding:6px 10px!important}
.da-qam-recents{gap:4px}
.da-qam-session-info{flex-direction:row;align-items:center;gap:6px}
.da-qam-session-info>.da-session-name{flex:1;min-width:0}
.da-qam-session-info>.da-status{padding-left:0;font-size:10px;flex-shrink:0}
.da-qam-recents>div{margin:0}
.da-qam-arrow{color:inherit;line-height:20px}

/* 输入区按钮共用 32px 高度和底边，所有状态均保持透明。 */
.da-app .da-composer .da-composer-actions{height:32px;min-height:32px;align-self:flex-end;align-items:center}
.da-app .da-composer .da-button.da-button{height:32px!important;min-height:32px!important;max-height:32px!important;align-self:flex-end;background:transparent!important;color:var(--text)!important;box-shadow:none!important;transition:none}
.da-app .da-composer .da-button.da-icon-button{width:32px!important;min-width:32px!important;max-width:32px!important;flex:0 0 32px!important;padding:0!important}
.da-app .da-composer .da-button.da-button:is(:hover,:active,:focus-visible,.gpfocus,[data-gpfocus="focus"],:disabled){background:transparent!important;color:var(--text)!important;box-shadow:none!important}
.da-app .da-composer .da-button.da-button:enabled:is(:focus-visible,.gpfocus,[data-gpfocus="focus"]){outline:1px solid var(--text)!important;outline-offset:-1px!important}

/* 输入框按整体高度居中，单行和多行输入保持同一轴线。 */
.da-app .da-composer{align-items:center;border-radius:8px}
.da-app .da-composer[data-multiline]{flex-wrap:wrap;row-gap:2px}
.da-app .da-composer[data-multiline] .da-compose-focus{order:-1;flex-basis:100%}
.da-app .da-composer[data-multiline] .da-composer-actions{margin-inline-start:auto}
.da-app .da-composer .da-composer-actions,.da-app .da-composer .da-button.da-button{align-self:center}
.da-app .da-composer .da-button-content{height:100%;align-items:center;justify-content:center}
.da-app .da-composer .da-model-picker{display:flex;align-items:center;justify-content:center;padding-top:0!important;padding-bottom:0!important}

/* 选中会话通过背景色区分。 */
.da-app .da-session-scroll>.da-button.active:not(:focus-visible):not(.gpfocus):not(:active),.da-app .da-qam-recents .da-button.active:not(:focus-visible):not(.gpfocus):not(:active){background:rgba(255,255,255,.38)!important;color:#fff!important}

/* 执行结束后的过程收为一行，最终答复保持可见。 */
.da-app .da-process{margin:0 0 14px}
.da-app .da-process .da-process-toggle.da-button{width:100%;justify-content:flex-start;text-align:left;background:transparent!important;color:var(--muted)!important;border-radius:0!important;box-shadow:none!important;border-bottom:1px solid var(--line)!important;padding:6px 0!important;font-size:12px!important;min-height:30px!important;transition:none!important}
.da-process-toggle>.da-button-content{justify-content:flex-start;gap:8px}
.da-process-count{font-size:11px}
.da-app .da-process .da-process-toggle.da-button:enabled:is(:focus-visible,.gpfocus){color:var(--text)!important;outline:1px solid var(--text)!important;outline-offset:2px!important}
.da-process-details{padding:12px 0 0 10px;border-left:1px solid var(--line);margin-top:6px}
.da-process-details .da-message:last-child{margin-bottom:0}

.da-app .da-process .da-process-toggle.da-button:enabled:is(:hover,:active,:focus-visible,.gpfocus,[data-gpfocus="focus"]){background:transparent!important;color:var(--text)!important;box-shadow:none!important}

.da-app .da-turn-interrupted{color:var(--muted);font-size:12px;line-height:1.5;margin:8px 0 16px}

`;
