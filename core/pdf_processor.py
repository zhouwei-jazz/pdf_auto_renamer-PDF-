import pdfplumber
import os
from typing import List, Dict, Optional, Tuple
import re
import unicodedata

class PDFTitleExtractor:
    def __init__(self):
        # 需要保留的文件编号模式
        self.code_pattern = r'(TM|STR|TEC|CSR|EPSM|FAM|HRM|MIS|IPR|MKT|OM|CPGN|SCLM)-\d+'
        # 页眉过滤参数
        self.header_threshold = 0.08  # 页面顶部8%区域视为页眉
        self.min_title_length = 2  # 最小标题长度
        # 字体大小阈值：视为同一字体大小的最大差异（点数）
        self.font_size_threshold = 0.5
        
    def extract_title_candidates(self, pdf_path: str) -> List[Tuple[str, float]]:
        """
        从PDF文件中提取标题候选列表
        返回：包含(文本, 字体大小)元组的列表
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) > 0:
                    first_page = pdf.pages[0]
                    
                    # 提取带有更多属性的单词
                    text_elements = first_page.extract_words(
                        extra_attrs=['size', 'top', 'fontname'],
                        keep_blank_chars=True,  # 保留空格
                        use_text_flow=True,     # 优化文本流识别
                        x_tolerance=3,          # 扩大水平容差，有助于连接同一行的文本
                        y_tolerance=3           # 扩大垂直容差，有助于连接同一段落的文本
                    )
                    
                    if not text_elements:
                        return [("未能识别标题", 0.0)]
                    
                    # 获取页面高度用于页眉判断
                    page_height = first_page.height
                    header_height = page_height * self.header_threshold
                    
                    # 过滤掉页眉区域的文本和数字页码
                    filtered_elements = [
                        elem for elem in text_elements
                        if not (elem['top'] < header_height or  # 不在页眉区域
                            elem['text'].isdigit() or  # 不是纯数字
                            len(elem['text'].strip()) < self.min_title_length)  # 不是过短的文本
                    ]
                    
                    if not filtered_elements:
                        return [("未能识别合适的标题", 0.0)]
                    
                    # 找出最大字体大小
                    max_font_size = max(elem['size'] for elem in filtered_elements)
                    
                    # 获取接近最大字体大小的元素（考虑字体差异范围）
                    large_font_elements = [
                        elem for elem in filtered_elements 
                        if max_font_size - elem['size'] <= self.font_size_threshold
                    ]
                    
                    # 按垂直位置和水平位置排序，以保持阅读顺序
                    sorted_elements = sorted(
                        large_font_elements,
                        key=lambda x: (x['top'], x['x0'])
                    )
                    
                    # 构建候选标题列表
                    candidates = []
                    
                    # 1. 提取最大字体的标题
                    max_font_title = self._join_text_elements(sorted_elements)
                    candidates.append((max_font_title, max_font_size))
                    
                    # 2. 尝试按行分组，提取可能的标题（处理多行标题）
                    line_groups = self._group_elements_by_line(sorted_elements)
                    if len(line_groups) > 1:
                        # 如果有多行，尝试使用第一行作为候选标题
                        first_line = self._join_text_elements(line_groups[0])
                        if first_line != max_font_title:
                            avg_size = sum(elem['size'] for elem in line_groups[0]) / len(line_groups[0])
                            candidates.append((first_line, avg_size))
                    
                    # 3. 如果还是没有好的候选项，尝试其他次大字体大小
                    if len(candidates) < 2:
                        unique_sizes = sorted(set(elem['size'] for elem in filtered_elements), reverse=True)
                        if len(unique_sizes) > 1:
                            second_size = unique_sizes[1]
                            second_elements = [elem for elem in filtered_elements if elem['size'] == second_size]
                            second_sorted = sorted(second_elements, key=lambda x: (x['top'], x['x0']))
                            second_title = self._join_text_elements(second_sorted)
                            candidates.append((second_title, second_size))
                    
                    return candidates
                else:
                    return [("PDF文件无页面", 0.0)]
                    
        except Exception as e:
            return [(f"处理出错: {str(e)}", 0.0)]
    
    def _join_text_elements(self, elements: List[Dict]) -> str:
        """智能连接文本元素，处理中英文混合情况"""
        if not elements:
            return ""
        
        # 按顺序连接文本
        texts = [elem['text'] for elem in elements]
        
        # 处理中英文连接
        result = ""
        for i, text in enumerate(texts):
            if i > 0:
                # 检查是否需要添加空格（避免中文之间、中英文之间不必要的空格）
                prev_char = texts[i-1][-1] if texts[i-1] else ""
                curr_char = text[0] if text else ""
                
                # 如果前一个字符是西文且当前字符也是西文，添加空格
                if (self._is_western_char(prev_char) and self._is_western_char(curr_char)):
                    result += " "
            
            result += text
                
        return result.strip()
    
    def _is_western_char(self, char: str) -> bool:
        """判断字符是否是西文字符（英文、数字、西文标点等）"""
        if not char:
            return False
        # 使用Unicode类别判断
        category = unicodedata.category(char)
        # 大部分西文字符属于Latin类别或标点、数字等
        return ('L' in category and not unicodedata.name(char, "").startswith('CJK')) or \
               category.startswith('P') or category.startswith('N')
    
    def _group_elements_by_line(self, elements: List[Dict]) -> List[List[Dict]]:
        """将文本元素按行分组"""
        if not elements:
            return []
            
        # 按垂直位置排序
        sorted_by_top = sorted(elements, key=lambda x: x['top'])
        
        line_groups = []
        current_line = [sorted_by_top[0]]
        current_top = sorted_by_top[0]['top']
        
        # 根据垂直位置的接近程度分组
        for elem in sorted_by_top[1:]:
            # 如果垂直位置接近当前行，认为是同一行
            if abs(elem['top'] - current_top) <= 5:  # 5点的容差
                current_line.append(elem)
            else:
                # 开始新行
                line_groups.append(sorted(current_line, key=lambda x: x['x0']))  # 按水平位置排序
                current_line = [elem]
                current_top = elem['top']
        
        # 添加最后一行
        if current_line:
            line_groups.append(sorted(current_line, key=lambda x: x['x0']))
            
        return line_groups
    
    def process_filename(self, title: str, original_filename: str) -> str:
        """
        处理文件名，确保其符合系统要求
        """
        # 获取原文件名（不含扩展名）
        original_name_without_ext = os.path.splitext(original_filename)[0]
        
        # 清理标题中的非法字符
        clean_title = self._clean_filename(title)
        
        # 控制长度
        max_length = 100
        if len(clean_title) > max_length:
            clean_title = clean_title[:max_length]
        
        # 组合新文件名（保留原文件名）
        new_filename = f"{clean_title}_{original_name_without_ext}.pdf"
        return new_filename
    
    def _clean_filename(self, filename: str) -> str:
        """
        清理文件名中的非法字符
        """
        # 替换Windows文件名中的非法字符
        illegal_chars = r'[\\/*?:"<>|]'
        clean_name = re.sub(illegal_chars, "", filename)
        # 替换连续的空格和点
        clean_name = re.sub(r'\s+', " ", clean_name)
        clean_name = re.sub(r'\.+', ".", clean_name)
        return clean_name.strip('. ')