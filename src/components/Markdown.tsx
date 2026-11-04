import { Children, isValidElement, memo, useState, type ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { platform } from '../client';
import { Button } from './ui';

const plugins = [remarkGfm];
function CodeBlock({ children }: { children?: ReactNode }) {
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);
  const child = Children.toArray(children)[0];
  const props = isValidElement<{ children?: ReactNode; className?: string }>(child) ? child.props : {};
  const language = props.className?.replace(/^language-/, '') || '代码';
  return <div className="da-code-block"><div className="da-code-head"><span>{language}</span><Button title="复制代码" onClick={() => {
    void navigator.clipboard.writeText(String(props.children || '').replace(/\n$/, '')).then(() => { setCopied(true); setFailed(false); }).catch(() => { setFailed(true); });
  }}>{failed ? '复制失败' : copied ? '已复制' : '复制'}</Button></div><pre>{children}</pre></div>;
}

function WebLink({ href, children }: { href?: string; children?: ReactNode }) {
  if (!href || !/^https?:\/\//i.test(href)) return <span>{children}</span>;
  return <a href={href} onClick={event => { event.preventDefault(); platform.external(href); }}>{children}</a>;
}

// React 节点渲染，保留默认 URL 过滤；消息中的 HTML 不作为页面执行。
export const Markdown = memo(function Markdown({ text }: { text: string }) {
  return <div className="da-markdown"><ReactMarkdown remarkPlugins={plugins} skipHtml components={{
    pre: CodeBlock,
    a: WebLink,
    img: ({ src, alt }) => <WebLink href={src}>图像：{alt || '查看图片'}</WebLink>,
    table: ({ children }) => <div className="da-table-scroll" tabIndex={0}><table>{children}</table></div>,
  }}>{text}</ReactMarkdown></div>;
});
