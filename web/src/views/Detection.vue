<template>
  <div class="detection">
    <div class="page-header">
      <h1>检测中心</h1>
      <p>上传图像或视频进行质量诊断</p>
    </div>
    
    <!-- 检测类型选择 -->
    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="单图检测" name="single">
        <div class="detection-content">
          <!-- 上传区域 -->
          <div class="upload-section">
            <el-upload
              ref="uploadRef"
              class="upload-area"
              drag
              :auto-upload="false"
              :show-file-list="false"
              accept="image/*"
              @change="handleImageChange"
            >
              <template v-if="!currentImage">
                <el-icon class="upload-icon"><UploadFilled /></el-icon>
                <div class="upload-text">
                  拖拽图像到此处，或 <em>点击上传</em>
                </div>
                <div class="upload-tip">支持 JPG、PNG、BMP 格式</div>
              </template>
              <template v-else>
                <img :src="imagePreview" class="preview-image" />
              </template>
            </el-upload>
            
            <div class="upload-options" v-if="currentImage">
              <el-form label-width="80px" size="small">
                <el-form-item label="配置模板">
                  <el-select v-model="detectOptions.profile">
                    <el-option label="严格模式" value="strict" />
                    <el-option label="标准模式" value="normal" />
                    <el-option label="宽松模式" value="loose" />
                  </el-select>
                </el-form-item>
                <el-form-item label="检测级别">
                  <el-select v-model="detectOptions.level">
                    <el-option label="快速检测" value="fast" />
                    <el-option label="标准检测" value="standard" />
                    <el-option label="深度检测" value="deep" />
                  </el-select>
                </el-form-item>
              </el-form>
              
              <div class="action-buttons">
                <el-button @click="clearImage">清除</el-button>
                <el-button type="primary" :loading="loading" @click="startDetection">
                  开始检测
                </el-button>
              </div>
            </div>
          </div>
          
          <!-- 检测结果 -->
          <div class="result-section" v-if="imageResult">
            <div class="result-header">
              <h3>检测结果</h3>
              <span :class="['status-tag', imageResult.is_abnormal ? 'abnormal' : 'normal']">
                {{ imageResult.is_abnormal ? '⚠️ 检测到异常' : '✅ 正常' }}
              </span>
            </div>
            
            <div class="result-summary" v-if="imageResult.is_abnormal">
              <div class="summary-item">
                <span class="label">主要问题:</span>
                <span class="value">{{ getIssueTypeName(imageResult.primary_issue) }}</span>
              </div>
              <div class="summary-item">
                <span class="label">严重程度:</span>
                <el-tag :type="getSeverityType(imageResult.severity)" size="small">
                  {{ getSeverityName(imageResult.severity) }}
                </el-tag>
              </div>
            </div>
            
            <div class="result-detectors">
              <h4>检测指标详情</h4>
              <div class="detector-grid">
                <div 
                  v-for="(det, idx) in imageResult.detection_results" 
                  :key="det.detector_name || det.issue_type || idx"
                  :class="['detector-card', { abnormal: det.is_abnormal }]"
                >
                  <div class="detector-icon">{{ getDetectorIcon(det.detector_name || det.type || det.issue_type) }}</div>
                  <div class="detector-info">
                    <div class="detector-name">{{ getDetectorName(det.detector_name || det.type || det.issue_type) }}</div>
                    <div class="detector-score">
                      {{ det.score?.toFixed(2) || 'N/A' }} / {{ det.threshold?.toFixed(2) || 'N/A' }}
                    </div>
                  </div>
                  <div :class="['detector-status', det.is_abnormal ? 'abnormal' : 'normal']">
                    {{ det.is_abnormal ? '异常' : '正常' }}
                  </div>
                </div>
              </div>
            </div>
            
            <div class="result-suggestions" v-if="imageResult.is_abnormal && abnormalDetectors.length > 0">
              <h4>💡 改进建议</h4>
              <ul>
                <li v-for="(det, idx) in abnormalDetectors" :key="idx">
                  <strong>{{ getDetectorName(det.detector_name || det.type || det.issue_type) }}:</strong>
                  <span v-if="det.suggestions && det.suggestions.length > 0">
                    {{ det.suggestions.join('；') }}
                  </span>
                  <span v-else-if="det.explanation">
                    {{ det.explanation }}
                  </span>
                  <span v-else>暂无具体建议</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="批量检测" name="batch">
        <div class="batch-content">
          <el-upload
            class="upload-area"
            drag
            multiple
            :auto-upload="false"
            accept="image/*"
            @change="handleBatchChange"
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="upload-text">
              拖拽多个图像到此处，或 <em>点击上传</em>
            </div>
            <div class="upload-tip">支持批量上传多个图像文件</div>
          </el-upload>
          
          <div v-if="batchFiles.length > 0" class="batch-results">
            <!-- 汇总统计卡片 -->
            <div v-if="batchSummary" class="batch-summary">
              <div class="summary-card">
                <div class="summary-label">总数量</div>
                <div class="summary-value">{{ batchSummary.total }}</div>
              </div>
              <div class="summary-card success">
                <div class="summary-label">正常</div>
                <div class="summary-value">{{ batchSummary.normal }}</div>
              </div>
              <div class="summary-card danger">
                <div class="summary-label">异常</div>
                <div class="summary-value">{{ batchSummary.abnormal }}</div>
              </div>
              <div class="summary-card">
                <div class="summary-label">异常率</div>
                <div class="summary-value">
                  {{ batchSummary.total > 0 ? ((batchSummary.abnormal / batchSummary.total) * 100).toFixed(1) : 0 }}%
                </div>
              </div>
            </div>
            
            <!-- 筛选工具栏 -->
            <div class="batch-filters">
              <el-radio-group v-model="batchFilter.status" size="small">
                <el-radio-button label="all">全部</el-radio-button>
                <el-radio-button label="normal">正常</el-radio-button>
                <el-radio-button label="abnormal">异常</el-radio-button>
              </el-radio-group>
              <el-input
                v-model="batchFilter.search"
                placeholder="搜索文件名"
                size="small"
                clearable
                style="width: 200px; margin-left: 12px;"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
            </div>
            
            <!-- 结果列表 -->
            <div class="batch-list">
              <el-table 
                :data="filteredBatchFiles" 
                stripe
                style="width: 100%"
                @row-click="viewBatchDetail"
              >
                <el-table-column label="缩略图" width="80">
                  <template #default="{ row }">
                    <img 
                      v-if="row.preview" 
                      :src="row.preview" 
                      class="batch-thumbnail"
                      @error="row.preview = ''"
                    />
                    <el-icon v-else :size="32"><Picture /></el-icon>
                  </template>
                </el-table-column>
                <el-table-column prop="name" label="文件名" min-width="200" show-overflow-tooltip />
                <el-table-column prop="size" label="大小" width="100">
                  <template #default="{ row }">
                    {{ formatSize(row.size) }}
                  </template>
                </el-table-column>
                <el-table-column label="状态" width="100">
                  <template #default="{ row }">
                    <el-tag 
                      :type="row.status === 'success' ? 'success' : row.status === 'error' ? 'danger' : 'info'" 
                      size="small"
                    >
                      {{ row.statusText || '待检测' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="检测结果" width="120">
                  <template #default="{ row }">
                    <span v-if="row.result">
                      <el-tag :type="row.result.is_abnormal ? 'danger' : 'success'" size="small">
                        {{ row.result.is_abnormal ? '⚠️ 异常' : '✅ 正常' }}
                      </el-tag>
                    </span>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column label="主要问题" width="150">
                  <template #default="{ row }">
                    <span v-if="row.result && row.result.primary_issue">
                      {{ getIssueTypeName(row.result.primary_issue) }}
                    </span>
                    <span v-else-if="row.result && !row.result.is_abnormal">正常</span>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column label="严重程度" width="100">
                  <template #default="{ row }">
                    <el-tag 
                      v-if="row.result"
                      :type="getSeverityType(row.result.severity)" 
                      size="small"
                    >
                      {{ getSeverityName(row.result.severity) }}
                    </el-tag>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column label="异常指标" width="100">
                  <template #default="{ row }">
                    <el-badge 
                      v-if="row.result"
                      :value="getAbnormalCount(row.result)" 
                      :type="getAbnormalCount(row.result) > 0 ? 'danger' : 'success'"
                    >
                      <span>{{ getAbnormalCount(row.result) }} / {{ getTotalDetectors(row.result) }}</span>
                    </el-badge>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="100" fixed="right">
                  <template #default="{ row }">
                    <el-button 
                      v-if="row.result"
                      text 
                      type="primary" 
                      size="small"
                      @click.stop="viewBatchDetail(row)"
                    >
                      查看详情
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            
            <div class="batch-actions">
              <el-button @click="clearBatch">清空列表</el-button>
              <el-button type="primary" :loading="loading" @click="startBatchDetection">
                开始批量检测
              </el-button>
            </div>
          </div>
          
          <!-- 详情侧边栏 -->
          <el-drawer
            v-model="showBatchDetail"
            :title="selectedBatchFile?.name || '检测详情'"
            size="600px"
            direction="rtl"
          >
            <div v-if="selectedBatchFile && selectedBatchFile.result" class="batch-detail">
              <!-- 图片预览 -->
              <div class="detail-preview">
                <img 
                  v-if="selectedBatchFile.preview" 
                  :src="selectedBatchFile.preview" 
                  class="detail-image"
                />
              </div>
              
              <!-- 结果概览 -->
              <div class="detail-summary">
                <div class="summary-item">
                  <span class="label">检测状态:</span>
                  <el-tag :type="selectedBatchFile.result.is_abnormal ? 'danger' : 'success'" size="small">
                    {{ selectedBatchFile.result.is_abnormal ? '异常' : '正常' }}
                  </el-tag>
                </div>
                <div class="summary-item" v-if="selectedBatchFile.result.primary_issue">
                  <span class="label">主要问题:</span>
                  <span class="value">{{ getIssueTypeName(selectedBatchFile.result.primary_issue) }}</span>
                </div>
                <div class="summary-item">
                  <span class="label">严重程度:</span>
                  <el-tag :type="getSeverityType(selectedBatchFile.result.severity)" size="small">
                    {{ getSeverityName(selectedBatchFile.result.severity) }}
                  </el-tag>
                </div>
              </div>
              
              <!-- 检测指标详情 -->
              <div class="detail-detectors">
                <h4>检测指标详情</h4>
                <div class="detector-grid">
                  <div 
                    v-for="(det, idx) in getDetailDetectors(selectedBatchFile.result)" 
                    :key="idx"
                    :class="['detector-card', { abnormal: det.is_abnormal }]"
                  >
                    <div class="detector-icon">{{ getDetectorIcon(det.detector_name || det.type || det.issue_type) }}</div>
                    <div class="detector-info">
                      <div class="detector-name">{{ getDetectorName(det.detector_name || det.type || det.issue_type) }}</div>
                      <div class="detector-score">
                        {{ det.score?.toFixed(2) || 'N/A' }} / {{ det.threshold?.toFixed(2) || 'N/A' }}
                      </div>
                    </div>
                    <div :class="['detector-status', det.is_abnormal ? 'abnormal' : 'normal']">
                      {{ det.is_abnormal ? '异常' : '正常' }}
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- 改进建议 -->
              <div class="detail-suggestions" v-if="getDetailAbnormalDetectors(selectedBatchFile.result).length > 0">
                <h4>💡 改进建议</h4>
                <ul>
                  <li v-for="(det, idx) in getDetailAbnormalDetectors(selectedBatchFile.result)" :key="idx">
                    <strong>{{ getDetectorName(det.detector_name || det.type || det.issue_type) }}:</strong>
                    <span v-if="det.suggestions && det.suggestions.length > 0">
                      {{ det.suggestions.join('；') }}
                    </span>
                    <span v-else-if="det.explanation">
                      {{ det.explanation }}
                    </span>
                  </li>
                </ul>
              </div>
            </div>
          </el-drawer>
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="视频检测" name="video">
        <div class="video-content">
          <el-upload
            class="upload-area"
            drag
            :auto-upload="false"
            :show-file-list="false"
            accept="video/*"
            @change="handleVideoChange"
          >
            <template v-if="!currentVideo">
              <el-icon class="upload-icon"><VideoCamera /></el-icon>
              <div class="upload-text">
                拖拽视频到此处，或 <em>点击上传</em>
              </div>
              <div class="upload-tip">支持 MP4、AVI、MOV 格式</div>
            </template>
            <template v-else>
              <div class="video-preview">
                <el-icon :size="48"><VideoCamera /></el-icon>
                <span>{{ currentVideo.name }}</span>
                <span class="video-size">{{ formatSize(currentVideo.size) }}</span>
              </div>
            </template>
          </el-upload>
          
          <div class="upload-options" v-if="currentVideo">
            <el-form label-width="80px" size="small">
              <el-form-item label="采样策略">
                <el-select v-model="videoOptions.sample_strategy">
                  <el-option label="固定间隔" value="interval" />
                  <el-option label="场景变化" value="scene" />
                  <el-option label="混合模式" value="hybrid" />
                </el-select>
              </el-form-item>
              <el-form-item label="采样间隔">
                <el-input-number v-model="videoOptions.sample_interval" :min="0.5" :max="5" :step="0.5" />
                <span class="unit">秒</span>
              </el-form-item>
            </el-form>
            
            <div class="action-buttons">
              <el-button @click="clearVideo">清除</el-button>
              <el-button type="primary" :loading="loading" @click="startVideoDetection">
                开始检测
              </el-button>
            </div>
          </div>
          
          <!-- 视频检测结果 -->
          <div class="result-section" v-if="videoResult">
            <div class="result-header">
              <h3>视频检测结果</h3>
              <span :class="['status-tag', videoResult.is_abnormal ? 'abnormal' : 'normal']">
                {{ videoResult.is_abnormal ? '⚠️ 检测到异常' : '✅ 正常' }}
              </span>
            </div>
            
            <div class="video-info">
              <div class="info-item">
                <span class="label">分辨率:</span>
                <span class="value">{{ videoResult.width }} × {{ videoResult.height }}</span>
              </div>
              <div class="info-item">
                <span class="label">时长:</span>
                <span class="value">{{ videoResult.duration.toFixed(1) }} 秒</span>
              </div>
              <div class="info-item">
                <span class="label">帧率:</span>
                <span class="value">{{ videoResult.fps.toFixed(1) }} fps</span>
              </div>
              <div class="info-item">
                <span class="label">采样帧数:</span>
                <span class="value">{{ videoResult.sampled_frames }}</span>
              </div>
              <div class="info-item">
                <span class="label">整体评分:</span>
                <span class="value">{{ videoResult.overall_score.toFixed(1) }}</span>
              </div>
            </div>
            
            <div class="result-issues" v-if="videoResult.issues?.length">
              <h4>问题时间段</h4>
              <el-timeline>
                <el-timeline-item 
                  v-for="(issue, idx) in videoResult.issues" 
                  :key="idx"
                  :color="issue.severity === 'error' ? '#f56c6c' : '#e6a23c'"
                >
                  <div class="issue-item">
                    <span class="issue-type">{{ getIssueTypeName(issue.issue_type) }}</span>
                    <span class="issue-time">{{ issue.start_time.toFixed(1) }}s - {{ issue.end_time.toFixed(1) }}s</span>
                  </div>
                </el-timeline-item>
              </el-timeline>
            </div>
          </div>
        </div>
      </el-tab-pane>
      
      <!-- 流检测标签页 -->
      <el-tab-pane label="流检测" name="stream">
        <div class="stream-content">
          <!-- 流管理区域 -->
          <div class="stream-management">
            <div class="stream-header">
              <h3>流检测管理</h3>
              <el-button type="primary" @click="showStreamDialog = true">
                <el-icon><Plus /></el-icon>
                添加流
              </el-button>
            </div>
            
            <!-- 流列表 -->
            <div class="stream-list" v-if="streams.length > 0">
              <el-card 
                v-for="stream in streams" 
                :key="stream.stream_id"
                class="stream-card"
                :class="{ 'stream-error': stream.status === 'error' || !stream.is_connected }"
              >
                <template #header>
                  <div class="stream-card-header">
                    <div class="stream-info">
                      <el-tag :type="stream.is_connected ? 'success' : 'danger'" size="small">
                        {{ stream.is_connected ? '已连接' : '未连接' }}
                      </el-tag>
                      <span class="stream-url">{{ stream.stream_url }}</span>
                    </div>
                    <div class="stream-actions">
                      <el-button 
                        size="small" 
                        @click="refreshStreamStatus(stream.stream_id)"
                        :loading="refreshingStreams.includes(stream.stream_id)"
                      >
                        刷新
                      </el-button>
                      <el-button 
                        type="danger" 
                        size="small" 
                        @click="stopStream(stream.stream_id)"
                      >
                        停止
                      </el-button>
                    </div>
                  </div>
                </template>
                
                <div class="stream-stats">
                  <div class="stat-item">
                    <span class="stat-label">状态:</span>
                    <el-tag :type="getStreamStatusType(stream.status)" size="small">
                      {{ getStreamStatusName(stream.status) }}
                    </el-tag>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">帧率:</span>
                    <span class="stat-value">{{ stream.fps.toFixed(1) }} fps</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">已接收帧数:</span>
                    <span class="stat-value">{{ stream.frames_received }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">已检测帧数:</span>
                    <span class="stat-value">{{ stream.frames_detected }}</span>
                  </div>
                  <div class="stat-item" v-if="stream.last_detection_time">
                    <span class="stat-label">最后检测:</span>
                    <span class="stat-value">{{ formatTime(stream.last_detection_time) }}</span>
                  </div>
                  <div class="stat-item" v-if="stream.connection_errors > 0">
                    <span class="stat-label">连接错误:</span>
                    <el-tag type="warning" size="small">{{ stream.connection_errors }}</el-tag>
                  </div>
                </div>
                
                <!-- 最新检测结果 -->
                <div class="stream-latest-result" v-if="streamLatestResults[stream.stream_id]">
                  <div class="result-header">
                    <span>最新检测结果</span>
                    <el-tag 
                      :type="streamLatestResults[stream.stream_id].is_abnormal ? 'danger' : 'success'"
                      size="small"
                    >
                      {{ streamLatestResults[stream.stream_id].is_abnormal ? '异常' : '正常' }}
                    </el-tag>
                  </div>
                  <div class="result-info" v-if="streamLatestResults[stream.stream_id].primary_issue">
                    <span class="label">主要问题:</span>
                    <span class="value">{{ getIssueTypeName(streamLatestResults[stream.stream_id].primary_issue) }}</span>
                  </div>
                  <el-button 
                    size="small" 
                    type="primary" 
                    link
                    @click="viewStreamResults(stream.stream_id)"
                  >
                    查看详细结果
                  </el-button>
                </div>
              </el-card>
            </div>
            
            <el-empty v-else description="暂无流检测任务" />
          </div>
          
          <!-- 添加流对话框 -->
          <el-dialog 
            v-model="showStreamDialog" 
            title="添加流检测" 
            width="600px"
            @close="resetStreamForm"
          >
            <el-form :model="streamForm" label-width="120px">
              <el-form-item label="流地址" required>
                <el-input 
                  v-model="streamForm.stream_url" 
                  placeholder="rtsp://192.168.1.100:554/stream 或 rtmp://example.com/live/stream"
                />
              </el-form-item>
              <el-form-item label="流类型">
                <el-radio-group v-model="streamForm.stream_type">
                  <el-radio label="rtsp">RTSP</el-radio>
                  <el-radio label="rtmp">RTMP</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="采样间隔">
                <el-input-number 
                  v-model="streamForm.sample_interval" 
                  :min="0.1" 
                  :max="10" 
                  :step="0.1"
                  :precision="1"
                />
                <span style="margin-left: 8px; color: #909399;">秒</span>
              </el-form-item>
              <el-form-item label="检测间隔">
                <el-input-number 
                  v-model="streamForm.detection_interval" 
                  :min="1" 
                  :max="60" 
                  :step="1"
                />
                <span style="margin-left: 8px; color: #909399;">秒</span>
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="showStreamDialog = false">取消</el-button>
              <el-button type="primary" :loading="startingStream" @click="startStream">
                启动检测
              </el-button>
            </template>
          </el-dialog>
          
          <!-- 流检测结果对话框 -->
          <el-dialog 
            v-model="showStreamResultsDialog" 
            :title="`流检测结果 - ${currentStreamId}`"
            width="900px"
          >
            <div class="stream-results-content">
              <div class="results-header">
                <el-pagination
                  v-model:current-page="streamResultsPage"
                  :page-size="streamResultsPageSize"
                  :total="streamResultsTotal"
                  layout="total, prev, pager, next"
                  @current-change="loadStreamResults"
                />
              </div>
              
              <el-table :data="streamResults" stripe style="width: 100%">
                <el-table-column prop="timestamp" label="检测时间" width="180">
                  <template #default="{ row }">
                    {{ formatTime(row.timestamp) }}
                  </template>
                </el-table-column>
                <el-table-column label="状态" width="80">
                  <template #default="{ row }">
                    <el-tag :type="row.is_abnormal ? 'danger' : 'success'" size="small">
                      {{ row.is_abnormal ? '异常' : '正常' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="primary_issue" label="主要问题" width="150">
                  <template #default="{ row }">
                    {{ getIssueTypeName(row.primary_issue) }}
                  </template>
                </el-table-column>
                <el-table-column prop="severity" label="严重程度" width="100">
                  <template #default="{ row }">
                    <el-tag :type="getSeverityType(row.severity)" size="small">
                      {{ getSeverityName(row.severity) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="fps" label="帧率" width="80">
                  <template #default="{ row }">
                    {{ row.fps.toFixed(1) }} fps
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="100">
                  <template #default="{ row }">
                    <el-button size="small" link @click="viewStreamResultDetail(row)">
                      查看详情
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-dialog>
        </div>
      </el-tab-pane>
      
      <!-- 基准对比标签页 -->
      <el-tab-pane label="基准对比" name="baseline">
        <div class="baseline-content">
          <el-tabs v-model="baselineActiveTab" type="border-card">
            <!-- 基准图像管理 -->
            <el-tab-pane label="基准图像管理" name="manage">
              <div class="baseline-management">
                <div class="baseline-header">
                  <h3>基准图像列表</h3>
                  <el-button type="primary" @click="showBaselineDialog = true">
                    <el-icon><Plus /></el-icon>
                    添加基准图像
                  </el-button>
                </div>
                
                <div class="baseline-list" v-if="baselines.length > 0">
                  <el-row :gutter="16">
                    <el-col 
                      v-for="baseline in baselines" 
                      :key="baseline.baseline_id"
                      :xs="24" :sm="12" :md="8" :lg="6"
                    >
                      <el-card class="baseline-card" shadow="hover">
                        <div class="baseline-image">
                          <img 
                            :src="getBaselineImageUrl(baseline.baseline_id)" 
                            @error="handleBaselineImageError"
                            alt="基准图像"
                          />
                        </div>
                        <div class="baseline-info">
                          <div class="baseline-name">{{ baseline.name }}</div>
                          <div class="baseline-description" v-if="baseline.description">
                            {{ baseline.description }}
                          </div>
                          <div class="baseline-tags" v-if="baseline.tags && baseline.tags.length > 0">
                            <el-tag 
                              v-for="tag in baseline.tags" 
                              :key="tag"
                              size="small"
                              style="margin-right: 4px;"
                            >
                              {{ tag }}
                            </el-tag>
                          </div>
                          <div class="baseline-time">
                            {{ formatTime(baseline.created_at) }}
                          </div>
                        </div>
                        <template #footer>
                          <div class="baseline-actions">
                            <el-button 
                              size="small" 
                              @click="useBaselineForCompare(baseline.baseline_id)"
                            >
                              使用对比
                            </el-button>
                            <el-button 
                              size="small" 
                              type="danger" 
                              @click="deleteBaseline(baseline.baseline_id)"
                            >
                              删除
                            </el-button>
                          </div>
                        </template>
                      </el-card>
                    </el-col>
                  </el-row>
                </div>
                
                <el-empty v-else description="暂无基准图像" />
              </div>
              
              <!-- 添加基准图像对话框 -->
              <el-dialog 
                v-model="showBaselineDialog" 
                title="添加基准图像" 
                width="600px"
                @close="resetBaselineForm"
              >
                <el-form :model="baselineForm" label-width="100px">
                  <el-form-item label="名称" required>
                    <el-input v-model="baselineForm.name" placeholder="请输入基准图像名称" />
                  </el-form-item>
                  <el-form-item label="描述">
                    <el-input 
                      v-model="baselineForm.description" 
                      type="textarea" 
                      :rows="3"
                      placeholder="请输入描述信息"
                    />
                  </el-form-item>
                  <el-form-item label="标签">
                    <el-input 
                      v-model="baselineForm.tags" 
                      placeholder="多个标签用逗号分隔"
                    />
                  </el-form-item>
                  <el-form-item label="图像" required>
                    <el-upload
                      ref="baselineUploadRef"
                      class="baseline-upload"
                      :auto-upload="false"
                      :show-file-list="false"
                      accept="image/*"
                      @change="handleBaselineImageChange"
                    >
                      <template v-if="!baselineForm.image">
                        <el-button>选择图像</el-button>
                      </template>
                      <template v-else>
                        <img :src="baselineImagePreview" class="baseline-preview" />
                      </template>
                    </el-upload>
                  </el-form-item>
                </el-form>
                <template #footer>
                  <el-button @click="showBaselineDialog = false">取消</el-button>
                  <el-button type="primary" :loading="savingBaseline" @click="saveBaseline">
                    保存
                  </el-button>
                </template>
              </el-dialog>
            </el-tab-pane>
            
            <!-- 基准对比检测 -->
            <el-tab-pane label="基准对比检测" name="compare">
              <div class="baseline-compare">
                <div class="compare-section">
                  <h3>选择基准图像</h3>
                  <el-select 
                    v-model="compareBaselineId" 
                    placeholder="选择基准图像"
                    style="width: 100%; margin-bottom: 16px;"
                    @change="loadBaselineInfo"
                  >
                    <el-option
                      v-for="baseline in baselines"
                      :key="baseline.baseline_id"
                      :label="baseline.name"
                      :value="baseline.baseline_id"
                    />
                  </el-select>
                  <el-button 
                    type="primary" 
                    link 
                    @click="showBaselineDialog = true"
                    style="margin-bottom: 16px;"
                  >
                    上传新基准图像
                  </el-button>
                
                <div class="baseline-preview" v-if="selectedBaseline">
                  <h4>基准图像</h4>
                  <img :src="getBaselineImageUrl(selectedBaseline.baseline_id)" alt="基准图像" />
                  <div class="baseline-info">
                    <div>{{ selectedBaseline.name }}</div>
                    <div v-if="selectedBaseline.description">{{ selectedBaseline.description }}</div>
                  </div>
                </div>
              </div>
              
              <div class="compare-section">
                <h3>上传待检测图像</h3>
                <el-upload
                  ref="compareUploadRef"
                  class="upload-area"
                  drag
                  :auto-upload="false"
                  :show-file-list="false"
                  accept="image/*"
                  @change="handleCompareImageChange"
                >
                  <template v-if="!compareImage">
                    <el-icon class="upload-icon"><UploadFilled /></el-icon>
                    <div class="upload-text">
                      拖拽图像到此处，或 <em>点击上传</em>
                    </div>
                    <div class="upload-tip">支持 JPG、PNG、BMP 格式</div>
                  </template>
                  <template v-else>
                    <img :src="compareImagePreview" class="preview-image" />
                  </template>
                </el-upload>
                
                <div class="upload-options" v-if="compareImage">
                  <el-form label-width="80px" size="small">
                    <el-form-item label="配置模板">
                      <el-select v-model="compareOptions.profile">
                        <el-option label="严格模式" value="strict" />
                        <el-option label="标准模式" value="normal" />
                        <el-option label="宽松模式" value="loose" />
                      </el-select>
                    </el-form-item>
                    <el-form-item label="检测级别">
                      <el-select v-model="compareOptions.level">
                        <el-option label="快速检测" value="fast" />
                        <el-option label="标准检测" value="standard" />
                        <el-option label="深度检测" value="deep" />
                      </el-select>
                    </el-form-item>
                  </el-form>
                  
                  <div class="action-buttons">
                    <el-button @click="clearCompareImage">清除</el-button>
                    <el-button type="primary" :loading="comparing" @click="startCompare">
                      开始对比
                    </el-button>
                  </div>
                </div>
              </div>
              
              <!-- 对比结果 -->
              <div class="compare-result" v-if="compareResult">
                <div class="result-header">
                  <h3>对比结果</h3>
                  <span :class="['status-tag', compareResult.is_abnormal ? 'abnormal' : 'normal']">
                    {{ compareResult.is_abnormal ? '⚠️ 检测到差异' : '✅ 相似度高' }}
                  </span>
                </div>
                
                <div class="result-summary">
                  <div class="summary-item">
                    <span class="label">整体相似度:</span>
                    <span class="value">{{ (compareResult.overall_similarity * 100).toFixed(1) }}%</span>
                  </div>
                  <div class="summary-item">
                    <span class="label">SSIM 相似度:</span>
                    <span class="value">{{ (compareResult.comparison_result.ssim_score * 100).toFixed(1) }}%</span>
                  </div>
                  <div class="summary-item">
                    <span class="label">直方图相似度:</span>
                    <span class="value">{{ (compareResult.comparison_result.histogram_similarity * 100).toFixed(1) }}%</span>
                  </div>
                  <div class="summary-item">
                    <span class="label">特征匹配度:</span>
                    <span class="value">{{ (compareResult.comparison_result.feature_match_score * 100).toFixed(1) }}%</span>
                  </div>
                </div>
                
                <div class="result-explanation" v-if="compareResult.explanation">
                  <h4>说明</h4>
                  <p>{{ compareResult.explanation }}</p>
                </div>
                
                <div class="result-suggestions" v-if="compareResult.suggestions && compareResult.suggestions.length > 0">
                  <h4>💡 改进建议</h4>
                  <ul>
                    <li v-for="(suggestion, idx) in compareResult.suggestions" :key="idx">
                      {{ suggestion }}
                    </li>
                  </ul>
                </div>
                
                <!-- 区域差异分析 -->
                <div class="region-differences" v-if="compareResult.comparison_result.region_differences?.length > 0">
                  <h4>区域差异分析</h4>
                  <div class="region-grid">
                    <div 
                      v-for="(region, idx) in compareResult.comparison_result.region_differences"
                      :key="idx"
                      :class="['region-item', { abnormal: region.is_abnormal }]"
                    >
                      <div class="region-label">区域 {{ region.region[0] + 1 }}-{{ region.region[1] + 1 }}</div>
                      <div class="region-ssim">SSIM: {{ (region.ssim * 100).toFixed(1) }}%</div>
                      <el-tag :type="region.is_abnormal ? 'danger' : 'success'" size="small">
                        {{ region.is_abnormal ? '异常' : '正常' }}
                      </el-tag>
                    </div>
                  </div>
                </div>
              </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useDetectionStore } from '@/stores/detection'
import { ElMessage } from 'element-plus'
import { UploadFilled, VideoCamera, Plus, Search } from '@element-plus/icons-vue'
import type { UploadFile } from 'element-plus'
import streamApi, { type StreamStatus, type StreamResult } from '@/api/stream'
import baselineApi, { type BaselineImage, type BaselineCompareResult } from '@/api/baseline'

const detectionStore = useDetectionStore()
const activeTab = ref('single')
const loading = ref(false)

// 单图检测
const currentImage = ref<File | null>(null)
const imagePreview = ref('')
const imageResult = ref<any>(null)
const detectOptions = ref({
  profile: 'normal',
  level: 'standard',
})

// 批量检测
const batchFiles = ref<any[]>([])
const batchSummary = ref<any>(null)
const batchFilter = ref({
  status: 'all', // all, normal, abnormal
  search: '',
})
const showBatchDetail = ref(false)
const selectedBatchFile = ref<any>(null)

// 视频检测
const currentVideo = ref<File | null>(null)
const videoResult = ref<any>(null)
const videoOptions = ref({
  sample_strategy: 'interval',
  sample_interval: 1.0,
})

// 流检测
const streams = ref<StreamStatus[]>([])
const streamLatestResults = ref<Record<string, StreamResult>>({})
const showStreamDialog = ref(false)
const startingStream = ref(false)
const refreshingStreams = ref<string[]>([])
const streamForm = ref({
  stream_url: '',
  stream_type: 'rtsp' as 'rtsp' | 'rtmp',
  sample_interval: 1.0,
  detection_interval: 5.0,
})
const showStreamResultsDialog = ref(false)
const currentStreamId = ref('')
const streamResults = ref<StreamResult[]>([])
const streamResultsPage = ref(1)
const streamResultsPageSize = ref(20)
const streamResultsTotal = ref(0)
let streamStatusInterval: number | null = null

// 基准对比
const baselines = ref<BaselineImage[]>([])
const baselineActiveTab = ref('manage')
const showBaselineDialog = ref(false)
const savingBaseline = ref(false)
const baselineForm = ref({
  name: '',
  description: '',
  tags: '',
  image: null as File | null,
})
const baselineImagePreview = ref('')
const compareBaselineId = ref('')
const selectedBaseline = ref<BaselineImage | null>(null)
const compareImage = ref<File | null>(null)
const compareImagePreview = ref('')
const comparing = ref(false)
const compareResult = ref<BaselineCompareResult | null>(null)
const compareOptions = ref({
  profile: 'normal',
  level: 'standard',
})

// 检测器映射（支持 detector_name 和 issue_type）
const DETECTOR_NAMES: Record<string, { name: string; icon: string }> = {
  blur: { name: '清晰度', icon: '🔍' },
  brightness: { name: '亮度', icon: '☀️' },
  contrast: { name: '对比度', icon: '◐' },
  color: { name: '色彩', icon: '🎨' },
  noise: { name: '噪声', icon: '🔊' },
  gaussian_noise: { name: '高斯噪声', icon: '🔊' }, // 高斯噪声
  salt_pepper_noise: { name: '椒盐噪声', icon: '🔊' }, // 椒盐噪声
  snow_noise: { name: '雪花噪声', icon: '🔊' }, // 雪花噪声
  stripe: { name: '条纹', icon: '📏' },
  occlusion: { name: '遮挡', icon: '🚧' },
  signal_loss: { name: '信号', icon: '📡' },
  signal: { name: '信号', icon: '📡' }, // 兼容 signal_normal
  freeze: { name: '画面冻结', icon: '❄️' },
  scene_change: { name: '场景变换', icon: '🔄' },
  shake: { name: '视频抖动', icon: '📳' },
  // 兼容 issue_type
  over_bright: { name: '过度曝光', icon: '☀️' },
  under_bright: { name: '曝光不足', icon: '🌙' },
  low_contrast: { name: '对比度过低', icon: '◐' },
  high_contrast: { name: '对比度过高', icon: '◑' },
  color_cast: { name: '色彩偏差', icon: '🎨' },
  desaturated: { name: '色彩饱和度低', icon: '🎨' },
}

const ISSUE_TYPE_NAMES: Record<string, string> = {
  normal: '正常',
  blur: '图像模糊',
  blur_normal: '清晰度正常',
  over_bright: '过度曝光',
  under_bright: '曝光不足',
  too_bright: '过度曝光',
  too_dark: '曝光不足',
  brightness_normal: '亮度正常',
  low_contrast: '对比度过低',
  high_contrast: '对比度过高',
  contrast_normal: '对比度正常',
  color_cast: '色彩偏差',
  desaturated: '色彩饱和度低',
  grayscale: '灰度图像',
  blue_screen: '蓝屏',
  green_screen: '绿屏',
  noise: '噪声干扰',
  noise_normal: '噪声正常',
  gaussian_noise: '高斯噪声', // 高斯噪声
  salt_pepper_noise: '椒盐噪声',
  snow_noise: '雪花噪声',
  stripe: '条纹干扰',
  stripe_normal: '条纹正常',
  occlusion: '画面遮挡',
  occlusion_normal: '遮挡检测正常',
  signal_loss: '信号丢失',
  signal_normal: '信号正常',
  black_screen: '黑屏',
  white_screen: '白屏',
  solid_color: '纯色画面',
  freeze: '画面冻结',
  scene_change: '场景变换异常',
  shake: '视频抖动',
}

const abnormalDetectors = computed(() => {
  if (!imageResult.value) return []
  const results = imageResult.value.detection_results || imageResult.value.issues || []
  return results.filter((d: any) => d.is_abnormal) || []
})

function getDetectorName(name: string | undefined) {
  if (!name) return '未知'
  
  // 如果名称以 _normal 结尾，提取基础类型
  if (name.endsWith('_normal')) {
    const baseType = name.replace('_normal', '')
    if (DETECTOR_NAMES[baseType]?.name) {
      return DETECTOR_NAMES[baseType].name
    }
    // 如果检测器映射中没有，尝试从问题类型映射中查找
    if (ISSUE_TYPE_NAMES[baseType]) {
      return ISSUE_TYPE_NAMES[baseType].replace('图像', '').replace('画面', '').replace('视频', '').trim()
    }
    return baseType
  }
  
  // 直接查找映射
  if (DETECTOR_NAMES[name]?.name) {
    return DETECTOR_NAMES[name].name
  }
  
  // 尝试从问题类型映射中查找
  if (ISSUE_TYPE_NAMES[name]) {
    return ISSUE_TYPE_NAMES[name].replace('图像', '').replace('画面', '').replace('视频', '').trim()
  }
  
  // 如果都不匹配，尝试提取基础类型（处理复合类型）
  const parts = name.split('_')
  if (parts.length > 1) {
    const baseType = parts[0]
    if (DETECTOR_NAMES[baseType]?.name) {
      return DETECTOR_NAMES[baseType].name
    }
    if (ISSUE_TYPE_NAMES[baseType]) {
      return ISSUE_TYPE_NAMES[baseType].replace('图像', '').replace('画面', '').replace('视频', '').trim()
    }
  }
  
  return name
}

function getDetectorIcon(name: string | undefined) {
  if (!name) return '📊'
  
  // 如果名称以 _normal 结尾，提取基础类型
  if (name.endsWith('_normal')) {
    const baseType = name.replace('_normal', '')
    return DETECTOR_NAMES[baseType]?.icon || '📊'
  }
  
  // 直接查找映射
  if (DETECTOR_NAMES[name]?.icon) {
    return DETECTOR_NAMES[name].icon
  }
  
  // 如果都不匹配，尝试提取基础类型（处理复合类型）
  const parts = name.split('_')
  if (parts.length > 1) {
    const baseType = parts[0]
    if (DETECTOR_NAMES[baseType]?.icon) {
      return DETECTOR_NAMES[baseType].icon
    }
  }
  
  return '📊'
}

function getIssueTypeName(type: string | null | undefined) {
  if (!type) return '未知'
  
  // 如果类型以 _normal 结尾，提取基础类型并显示"正常"
  if (type.endsWith('_normal')) {
    const baseType = type.replace('_normal', '')
    const baseName = ISSUE_TYPE_NAMES[baseType] || DETECTOR_NAMES[baseType]?.name || baseType
    return `${baseName} - 正常`
  }
  
  // 直接查找映射
  if (ISSUE_TYPE_NAMES[type]) {
    return ISSUE_TYPE_NAMES[type]
  }
  
  // 尝试从检测器名称映射中查找
  if (DETECTOR_NAMES[type]?.name) {
    return DETECTOR_NAMES[type].name
  }
  
  // 如果都不匹配，尝试提取基础类型（处理复合类型）
  const parts = type.split('_')
  if (parts.length > 1) {
    const baseType = parts[0]
    if (ISSUE_TYPE_NAMES[baseType]) {
      return ISSUE_TYPE_NAMES[baseType]
    }
    if (DETECTOR_NAMES[baseType]?.name) {
      return DETECTOR_NAMES[baseType].name
    }
  }
  
  return type
}

function getSeverityType(severity: string) {
  const map: Record<string, string> = {
    normal: 'success',
    info: 'info',
    warning: 'warning',
    error: 'danger',
  }
  return map[severity] || 'info'
}

function getSeverityName(severity: string) {
  const map: Record<string, string> = {
    normal: '正常',
    info: '提示',
    warning: '警告',
    error: '严重',
  }
  return map[severity] || severity
}

function formatSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function handleImageChange(file: UploadFile) {
  if (file.raw) {
    currentImage.value = file.raw
    imagePreview.value = URL.createObjectURL(file.raw)
    imageResult.value = null
  }
}

function clearImage() {
  currentImage.value = null
  imagePreview.value = ''
  imageResult.value = null
}

async function startDetection() {
  if (!currentImage.value) return
  
  loading.value = true
  try {
    const result = await detectionStore.diagnoseImage(currentImage.value, detectOptions.value)
    // 转换数据结构：后端返回的是 issues，需要转换为 detection_results 格式
    if (result && result.issues) {
      imageResult.value = {
        ...result,
        detection_results: result.issues.map((issue: any) => ({
          detector_name: issue.type, // 使用 type 作为 detector_name
          is_abnormal: issue.is_abnormal,
          score: issue.score,
          threshold: issue.threshold,
          confidence: issue.confidence,
          issue_type: issue.type,
          explanation: issue.explanation,
          suggestions: issue.suggestions || [],
        })),
      }
    } else {
      imageResult.value = result
    }
  } catch (error) {
    ElMessage.error('检测失败，请稍后重试')
    console.error('检测错误:', error)
  } finally {
    loading.value = false
  }
}

function handleBatchChange(file: UploadFile) {
  if (file.raw) {
    // 生成预览图
    const preview = URL.createObjectURL(file.raw)
    batchFiles.value.push({
      file: file.raw,
      name: file.name,
      size: file.raw.size,
      preview: preview,
      status: 'pending',
      statusText: '待检测',
      result: null,
    })
  }
}

function clearBatch() {
  batchFiles.value = []
  batchSummary.value = null
  batchFilter.value = { status: 'all', search: '' }
  showBatchDetail.value = false
  selectedBatchFile.value = null
}

// 筛选后的文件列表
const filteredBatchFiles = computed(() => {
  let files = batchFiles.value
  
  // 状态筛选
  if (batchFilter.value.status !== 'all') {
    if (batchFilter.value.status === 'normal') {
      files = files.filter(f => f.result && !f.result.is_abnormal)
    } else if (batchFilter.value.status === 'abnormal') {
      files = files.filter(f => f.result && f.result.is_abnormal)
    }
  }
  
  // 搜索筛选
  if (batchFilter.value.search) {
    const search = batchFilter.value.search.toLowerCase()
    files = files.filter(f => f.name.toLowerCase().includes(search))
  }
  
  return files
})

// 获取异常指标数量
function getAbnormalCount(result: any) {
  if (!result) return 0
  const detectors = result.detection_results || result.issues || []
  return detectors.filter((d: any) => d.is_abnormal).length
}

// 获取总指标数量
function getTotalDetectors(result: any) {
  if (!result) return 0
  const detectors = result.detection_results || result.issues || []
  return detectors.length
}

// 获取详情中的检测器列表
function getDetailDetectors(result: any) {
  if (!result) return []
  const detectors = result.detection_results || result.issues || []
  return detectors
}

// 获取详情中的异常检测器列表
function getDetailAbnormalDetectors(result: any) {
  if (!result) return []
  const detectors = result.detection_results || result.issues || []
  return detectors.filter((d: any) => d.is_abnormal)
}

// 查看详情
function viewBatchDetail(row: any) {
  if (!row.result) {
    ElMessage.warning('该文件尚未完成检测')
    return
  }
  selectedBatchFile.value = row
  showBatchDetail.value = true
}

async function startBatchDetection() {
  if (batchFiles.value.length === 0) return
  
  loading.value = true
  try {
    const files = batchFiles.value.map(f => f.file)
    const result = await detectionStore.diagnoseBatch(files, detectOptions.value)
    
    // 更新文件状态和结果
    if (result && result.results) {
      result.results.forEach((item: any, index: number) => {
        if (batchFiles.value[index]) {
          // 转换数据结构
          const convertedResult = {
            ...item,
            detection_results: item.issues ? item.issues.map((issue: any) => ({
              detector_name: issue.type?.replace('_normal', '') || '',
              is_abnormal: issue.is_abnormal,
              score: issue.score,
              threshold: issue.threshold,
              confidence: issue.confidence,
              issue_type: issue.type,
              type: issue.type,
              explanation: issue.explanation,
              suggestions: issue.suggestions || [],
            })) : item.detection_results || [],
          }
          
          batchFiles.value[index].status = item.is_abnormal ? 'error' : 'success'
          batchFiles.value[index].statusText = item.is_abnormal ? '异常' : '正常'
          batchFiles.value[index].result = convertedResult
        }
      })
      
      // 计算汇总统计
      const total = result.results.length
      const normal = result.results.filter((r: any) => !r.is_abnormal).length
      const abnormal = result.results.filter((r: any) => r.is_abnormal).length
      batchSummary.value = {
        total,
        normal,
        abnormal,
      }
    } else if (result && result.summary) {
      // 如果有汇总信息，更新汇总统计
      batchSummary.value = {
        total: result.summary.total_images || batchFiles.value.length,
        normal: result.summary.normal_count || 0,
        abnormal: result.summary.abnormal_count || 0,
      }
    }
    
    ElMessage.success('批量检测完成')
  } catch (error) {
    ElMessage.error('批量检测失败')
    console.error('批量检测错误:', error)
    // 更新失败状态
    batchFiles.value.forEach(file => {
      if (file.status === 'pending') {
        file.status = 'error'
        file.statusText = '检测失败'
      }
    })
  } finally {
    loading.value = false
  }
}

function handleVideoChange(file: UploadFile) {
  if (file.raw) {
    currentVideo.value = file.raw
    videoResult.value = null
  }
}

function clearVideo() {
  currentVideo.value = null
  videoResult.value = null
}

// 流检测相关函数
async function loadStreams() {
  try {
    const response = await streamApi.listStreams()
    streams.value = response.streams || []
    
    // 为每个流加载最新结果
    for (const stream of streams.value) {
      if (stream.status === 'running') {
        loadStreamLatestResult(stream.stream_id)
      }
    }
  } catch (error) {
    console.error('加载流列表失败:', error)
  }
}

async function loadStreamLatestResult(streamId: string) {
  try {
    const response = await streamApi.getStreamResults(streamId, { limit: 1 })
    if (response.results && response.results.length > 0) {
      streamLatestResults.value[streamId] = response.results[0]
    }
  } catch (error) {
    console.error('加载流最新结果失败:', error)
  }
}

async function startStream() {
  if (!streamForm.value.stream_url) {
    ElMessage.warning('请输入流地址')
    return
  }
  
  startingStream.value = true
  try {
    await streamApi.startStream({
      stream_url: streamForm.value.stream_url,
      stream_type: streamForm.value.stream_type,
      sample_interval: streamForm.value.sample_interval,
      detection_interval: streamForm.value.detection_interval,
    })
    ElMessage.success('流检测已启动')
    showStreamDialog.value = false
    resetStreamForm()
    await loadStreams()
  } catch (error: any) {
    ElMessage.error(error.message || '启动流检测失败')
  } finally {
    startingStream.value = false
  }
}

async function stopStream(streamId: string) {
  try {
    await streamApi.stopStream(streamId)
    ElMessage.success('流检测已停止')
    await loadStreams()
  } catch (error: any) {
    ElMessage.error(error.message || '停止流检测失败')
  }
}

async function refreshStreamStatus(streamId: string) {
  if (refreshingStreams.value.includes(streamId)) return
  
  refreshingStreams.value.push(streamId)
  try {
    const status = await streamApi.getStreamStatus(streamId)
    const index = streams.value.findIndex(s => s.stream_id === streamId)
    if (index >= 0) {
      streams.value[index] = status
    }
    await loadStreamLatestResult(streamId)
  } catch (error) {
    console.error('刷新流状态失败:', error)
  } finally {
    const idx = refreshingStreams.value.indexOf(streamId)
    if (idx >= 0) {
      refreshingStreams.value.splice(idx, 1)
    }
  }
}

function resetStreamForm() {
  streamForm.value = {
    stream_url: '',
    stream_type: 'rtsp',
    sample_interval: 1.0,
    detection_interval: 5.0,
  }
}

function getStreamStatusType(status: string) {
  const map: Record<string, string> = {
    running: 'success',
    stopped: 'info',
    error: 'danger',
  }
  return map[status] || 'info'
}

function getStreamStatusName(status: string) {
  const map: Record<string, string> = {
    running: '运行中',
    stopped: '已停止',
    error: '错误',
  }
  return map[status] || status
}

function formatTime(timeStr: string) {
  if (!timeStr) return ''
  try {
    const date = new Date(timeStr)
    return date.toLocaleString('zh-CN')
  } catch {
    return timeStr
  }
}

async function viewStreamResults(streamId: string) {
  currentStreamId.value = streamId
  showStreamResultsDialog.value = true
  await loadStreamResults()
}

async function loadStreamResults() {
  try {
    const response = await streamApi.getStreamResults(currentStreamId.value, {
      limit: streamResultsPageSize.value,
    })
    streamResults.value = response.results || []
    streamResultsTotal.value = response.total || 0
  } catch (error) {
    console.error('加载流检测结果失败:', error)
  }
}

function viewStreamResultDetail(result: StreamResult) {
  // 可以打开详情对话框显示更详细的信息
  ElMessage.info('查看详情功能开发中')
}

// 基准对比相关函数
async function loadBaselines() {
  try {
    const response = await baselineApi.listBaselines()
    baselines.value = response.baselines || []
  } catch (error) {
    console.error('加载基准图像列表失败:', error)
  }
}

function getBaselineImageUrl(baselineId: string) {
  return `/api/v1/baseline/images/${baselineId}/image`
}

function handleBaselineImageError(event: Event) {
  // 处理图像加载错误
  const img = event.target as HTMLImageElement
  img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2Y1ZjVmNSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LXNpemU9IjE0IiBmaWxsPSIjOTk5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+5Zu+54mH5pyq5Yqg6L29PC90ZXh0Pjwvc3ZnPg=='
}

function handleBaselineImageChange(file: UploadFile) {
  if (file.raw) {
    baselineForm.value.image = file.raw
    baselineImagePreview.value = URL.createObjectURL(file.raw)
  }
}

function resetBaselineForm() {
  baselineForm.value = {
    name: '',
    description: '',
    tags: '',
    image: null,
  }
  baselineImagePreview.value = ''
}

async function saveBaseline() {
  if (!baselineForm.value.name) {
    ElMessage.warning('请输入基准图像名称')
    return
  }
  if (!baselineForm.value.image) {
    ElMessage.warning('请选择图像')
    return
  }
  
  savingBaseline.value = true
  try {
    const tags = baselineForm.value.tags
      ? baselineForm.value.tags.split(',').map(t => t.trim()).filter(t => t)
      : []
    
    await baselineApi.createBaseline({
      name: baselineForm.value.name,
      description: baselineForm.value.description || undefined,
      tags: tags.length > 0 ? tags : undefined,
      image: baselineForm.value.image,
    })
    
    ElMessage.success('基准图像已保存')
    showBaselineDialog.value = false
    resetBaselineForm()
    await loadBaselines()
  } catch (error: any) {
    ElMessage.error(error.message || '保存基准图像失败')
  } finally {
    savingBaseline.value = false
  }
}

async function deleteBaseline(baselineId: string) {
  try {
    await baselineApi.deleteBaseline(baselineId)
    ElMessage.success('基准图像已删除')
    await loadBaselines()
    if (compareBaselineId.value === baselineId) {
      compareBaselineId.value = ''
      selectedBaseline.value = null
    }
  } catch (error: any) {
    ElMessage.error(error.message || '删除基准图像失败')
  }
}

function useBaselineForCompare(baselineId: string) {
  compareBaselineId.value = baselineId
  baselineActiveTab.value = 'compare'
  loadBaselineInfo()
}

function loadBaselineInfo() {
  if (compareBaselineId.value) {
    selectedBaseline.value = baselines.value.find(b => b.baseline_id === compareBaselineId.value) || null
  } else {
    selectedBaseline.value = null
  }
}

function handleCompareImageChange(file: UploadFile) {
  if (file.raw) {
    compareImage.value = file.raw
    compareImagePreview.value = URL.createObjectURL(file.raw)
    compareResult.value = null
  }
}

function clearCompareImage() {
  compareImage.value = null
  compareImagePreview.value = ''
  compareResult.value = null
}

async function startCompare() {
  if (!compareImage.value) {
    ElMessage.warning('请选择待检测图像')
    return
  }
  if (!compareBaselineId.value && !selectedBaseline.value) {
    ElMessage.warning('请选择基准图像')
    return
  }
  
  comparing.value = true
  try {
    const result = await baselineApi.compareWithBaseline({
      image: compareImage.value,
      baseline_id: compareBaselineId.value || undefined,
      profile: compareOptions.value.profile,
      level: compareOptions.value.level,
    })
    compareResult.value = result
  } catch (error: any) {
    ElMessage.error(error.message || '对比检测失败')
  } finally {
    comparing.value = false
  }
}

// 生命周期
onMounted(() => {
  // 如果当前标签是流检测，加载流列表
  if (activeTab.value === 'stream') {
    loadStreams()
    // 每5秒刷新一次流状态
    streamStatusInterval = window.setInterval(() => {
      loadStreams()
    }, 5000)
  }
  
  // 如果当前标签是基准对比，加载基准图像列表
  if (activeTab.value === 'baseline') {
    loadBaselines()
  }
})

onUnmounted(() => {
  if (streamStatusInterval) {
    clearInterval(streamStatusInterval)
  }
})

// 监听标签切换
watch(activeTab, (newTab) => {
  if (newTab === 'stream') {
    loadStreams()
    if (!streamStatusInterval) {
      streamStatusInterval = window.setInterval(() => {
        loadStreams()
      }, 5000)
    }
  } else {
    if (streamStatusInterval) {
      clearInterval(streamStatusInterval)
      streamStatusInterval = null
    }
  }
  
  if (newTab === 'baseline') {
    loadBaselines()
  }
})

async function startVideoDetection() {
  if (!currentVideo.value) return
  
  loading.value = true
  try {
    videoResult.value = await detectionStore.diagnoseVideo(currentVideo.value, videoOptions.value)
  } catch (error) {
    ElMessage.error('视频检测失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.detection {
  max-width: 1200px;
  margin: 0 auto;
}

.detection-content,
.batch-content,
.video-content {
  display: grid;
  gap: 24px;
}

.upload-section {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 24px;
  
  @media (max-width: 800px) {
    grid-template-columns: 1fr;
  }
}

.upload-area {
  :deep(.el-upload-dragger) {
    width: 100%;
    height: 300px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    border-radius: 12px;
  }
  
  .preview-image {
    max-width: 100%;
    max-height: 280px;
    object-fit: contain;
    border-radius: 8px;
  }
}

.upload-options {
  background: #fff;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  
  .action-buttons {
    margin-top: 20px;
    display: flex;
    gap: 12px;
    justify-content: flex-end;
  }
  
  .unit {
    margin-left: 8px;
    color: #909399;
  }
}

.result-section {
  background: #fff;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  
  h3 {
    font-size: 18px;
    font-weight: 600;
  }
}

.result-summary {
  display: flex;
  gap: 24px;
  padding: 16px;
  background: #fef0f0;
  border-radius: 8px;
  margin-bottom: 20px;
  
  .summary-item {
    display: flex;
    align-items: center;
    gap: 8px;
    
    .label {
      color: #909399;
    }
    
    .value {
      font-weight: 600;
      color: #f56c6c;
    }
  }
}

.result-detectors {
  h4 {
    font-size: 14px;
    color: #606266;
    margin-bottom: 16px;
  }
}

.detector-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.detector-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
  border: 1px solid transparent;
  
  &.abnormal {
    background: #fef0f0;
    border-color: #f56c6c;
  }
  
  .detector-icon {
    font-size: 24px;
  }
  
  .detector-info {
    flex: 1;
    
    .detector-name {
      font-weight: 500;
      margin-bottom: 2px;
    }
    
    .detector-score {
      font-size: 12px;
      color: #909399;
    }
  }
  
  .detector-status {
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 4px;
    
    &.normal {
      background: rgba(103, 194, 58, 0.1);
      color: #67c23a;
    }
    
    &.abnormal {
      background: rgba(245, 108, 108, 0.1);
      color: #f56c6c;
    }
  }
}

.result-suggestions {
  margin-top: 20px;
  padding: 16px;
  background: #f0f9eb;
  border-radius: 8px;
  
  h4 {
    margin-bottom: 12px;
    font-size: 14px;
  }
  
  ul {
    margin: 0;
    padding-left: 20px;
    
    li {
      margin-bottom: 8px;
      color: #606266;
      
      strong {
        color: #303133;
      }
    }
  }
}

.video-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #606266;
  
  .video-size {
    font-size: 12px;
    color: #909399;
  }
}

.video-info {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 16px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 20px;
  
  .info-item {
    .label {
      font-size: 12px;
      color: #909399;
      display: block;
      margin-bottom: 4px;
    }
    
    .value {
      font-weight: 600;
      color: #303133;
    }
  }
}

.result-issues {
  h4 {
    margin-bottom: 16px;
    font-size: 14px;
  }
  
  .issue-item {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .issue-type {
      font-weight: 500;
    }
    
    .issue-time {
      font-size: 12px;
      color: #909399;
    }
  }
}

.batch-results {
  margin-top: 20px;
}

.batch-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
  
  .summary-card {
    background: #fff;
    padding: 16px;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    text-align: center;
    
    &.success {
      border-left: 4px solid #67c23a;
    }
    
    &.danger {
      border-left: 4px solid #f56c6c;
    }
    
    .summary-label {
      font-size: 12px;
      color: #909399;
      margin-bottom: 8px;
    }
    
    .summary-value {
      font-size: 24px;
      font-weight: 600;
      color: #303133;
    }
  }
}

.batch-filters {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.batch-list {
  background: #fff;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  
  .batch-thumbnail {
    width: 60px;
    height: 60px;
    object-fit: cover;
    border-radius: 4px;
    cursor: pointer;
  }
  
  :deep(.el-table__row) {
    cursor: pointer;
    
    &:hover {
      background-color: #f5f7fa;
    }
  }
}

.batch-actions {
  margin-top: 16px;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.batch-detail {
  .detail-preview {
    margin-bottom: 20px;
    text-align: center;
    
    .detail-image {
      max-width: 100%;
      max-height: 300px;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
  }
  
  .detail-summary {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
    background: #f5f7fa;
    border-radius: 8px;
    margin-bottom: 20px;
    
    .summary-item {
      display: flex;
      align-items: center;
      gap: 8px;
      
      .label {
        color: #909399;
        font-size: 14px;
      }
      
      .value {
        font-weight: 600;
        color: #303133;
      }
    }
  }
  
  .detail-detectors {
    margin-bottom: 20px;
    
    h4 {
      font-size: 16px;
      margin-bottom: 16px;
      color: #303133;
    }
  }
  
  .detail-suggestions {
    padding: 16px;
    background: #f0f9eb;
    border-radius: 8px;
    
    h4 {
      margin-bottom: 12px;
      font-size: 14px;
    }
    
    ul {
      margin: 0;
      padding-left: 20px;
      
      li {
        margin-bottom: 8px;
        color: #606266;
        line-height: 1.6;
        
        strong {
          color: #303133;
        }
      }
    }
  }
}

// 流检测样式
.stream-management {
  .stream-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    h3 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
    }
  }
  
  .stream-list {
    display: grid;
    gap: 16px;
  }
  
  .stream-card {
    margin-bottom: 16px;
    
    &.stream-error {
      border-color: #f56c6c;
    }
    
    .stream-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      .stream-info {
        display: flex;
        align-items: center;
        gap: 12px;
        
        .stream-url {
          font-family: monospace;
          color: #606266;
          font-size: 14px;
        }
      }
      
      .stream-actions {
        display: flex;
        gap: 8px;
      }
    }
    
    .stream-stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
      
      .stat-item {
        display: flex;
        align-items: center;
        gap: 8px;
        
        .stat-label {
          color: #909399;
          font-size: 14px;
        }
        
        .stat-value {
          font-weight: 600;
          color: #303133;
        }
      }
    }
    
    .stream-latest-result {
      padding: 12px;
      background: #f5f7fa;
      border-radius: 8px;
      margin-top: 12px;
      
      .result-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
      }
      
      .result-info {
        margin-bottom: 8px;
        font-size: 14px;
        
        .label {
          color: #909399;
        }
        
        .value {
          color: #303133;
          font-weight: 500;
        }
      }
    }
  }
}

.stream-results-content {
  .results-header {
    margin-bottom: 16px;
    display: flex;
    justify-content: flex-end;
  }
}

// 基准对比样式
.baseline-management {
  .baseline-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    h3 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
    }
  }
  
  .baseline-list {
    margin-top: 20px;
  }
  
  .baseline-card {
    margin-bottom: 16px;
    height: 100%;
    
    .baseline-image {
      width: 100%;
      height: 200px;
      overflow: hidden;
      border-radius: 8px;
      margin-bottom: 12px;
      background: #f5f7fa;
      display: flex;
      align-items: center;
      justify-content: center;
      
      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
    }
    
    .baseline-info {
      .baseline-name {
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 8px;
        color: #303133;
      }
      
      .baseline-description {
        font-size: 14px;
        color: #606266;
        margin-bottom: 8px;
        line-height: 1.5;
      }
      
      .baseline-tags {
        margin-bottom: 8px;
      }
      
      .baseline-time {
        font-size: 12px;
        color: #909399;
      }
    }
    
    .baseline-actions {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
    }
  }
  
  .baseline-upload {
    :deep(.el-upload) {
      width: 100%;
    }
    
    .baseline-preview {
      max-width: 100%;
      max-height: 300px;
      border-radius: 8px;
    }
  }
}

.baseline-compare {
  .compare-section {
    margin-bottom: 32px;
    
    h3 {
      font-size: 18px;
      font-weight: 600;
      margin-bottom: 16px;
    }
    
    h4 {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 12px;
    }
  }
  
  .baseline-preview {
    margin-top: 16px;
    padding: 16px;
    background: #f5f7fa;
    border-radius: 8px;
    
    img {
      max-width: 100%;
      max-height: 300px;
      border-radius: 8px;
      margin-bottom: 12px;
    }
    
    .baseline-info {
      font-size: 14px;
      color: #606266;
    }
  }
  
  .compare-result {
    margin-top: 24px;
    padding: 24px;
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
    
    .result-explanation {
      margin-top: 20px;
      padding: 16px;
      background: #f0f9eb;
      border-radius: 8px;
      
      h4 {
        margin-bottom: 12px;
        font-size: 14px;
      }
      
      p {
        margin: 0;
        color: #606266;
        line-height: 1.6;
      }
    }
    
    .region-differences {
      margin-top: 20px;
      
      h4 {
        margin-bottom: 16px;
        font-size: 14px;
      }
      
      .region-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
        gap: 12px;
        
        .region-item {
          padding: 12px;
          border: 1px solid #dcdfe6;
          border-radius: 8px;
          text-align: center;
          
          &.abnormal {
            border-color: #f56c6c;
            background: #fef0f0;
          }
          
          .region-label {
            font-size: 12px;
            color: #909399;
            margin-bottom: 4px;
          }
          
          .region-ssim {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 8px;
            color: #303133;
          }
        }
      }
    }
  }
}
</style>

