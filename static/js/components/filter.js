import {eventBus} from "../event-bus.js";

// language=Vue
const template = `
  <div class="accordion mb-1" id="filters">
    <div class="accordion-item">
      <h5 class="accordion-header">
        <button class="accordion-button btn-sm p-1" type="button" data-bs-toggle="collapse"
                data-bs-target="#filter-collapse" aria-expanded="true" aria-controls="filter-collapse"
                @click="toggleFilterAccordion" :class="{collapsed: !settings.filterAccordionOpen}">
          Filter
        </button>
      </h5>
    </div>
    <div class="accordion-item">
      <div id="filter-collapse" class="accordion-collapse collapse" :class="{ show: settings.filterAccordionOpen }">
        <div class="accordion-body p-1">
          <div class="input-group d-flex justify-content-center align-items-start mb-2 gap-2">
            <select v-model="selectedFolder" class="form-select form-control w-auto">
              <option value="">All Folders</option>
              <option value="~root~">Root Folder</option>
              <option v-for="folder in uniqueFolders" :key="folder" :value="folder">{{ folder }}</option>
            </select>
            <div class="d-flex align-items-center flex-column flex-sm-row gap-1">
              <select v-model="currentSort" class="form-select form-control w-auto ms-2">
                <option value="created">Sort by Time</option>
                <option value="folder created">Sort by Folder and Time</option>
                <option value="filesize">Sort by Size</option>
                <option value="duration">Sort by Duration</option>
              </select>
              <div class="btn-group" role="group" aria-label="Sort Direction">
                <button type="button" class="btn btn-sm btn-outline-secondary" :class="{ active: currentSortDir === 'asc' }" @click="currentSortDir = 'asc'">
                  <i class="bi bi-arrow-up"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" :class="{ active: currentSortDir === 'desc' }" @click="currentSortDir = 'desc'">
                  <i class="bi bi-arrow-down"></i>
                </button>
              </div>
            </div>
          </div>

          <div class="d-flex flex-column flex-lg-row justify-content-between mb-2 gap-2">
            <div class="btn-group" role="group" aria-label="Filter by Resolution">
              <button type="button" class="btn btn-outline-secondary btn-sm" :class="{ active: selectedResolution === '' }" @click="selectedResolution = ''">All&nbsp;Resolutions</button>
              <button type="button" class="btn btn-outline-secondary btn-sm p-1" :class="{ active: selectedResolution === 'HD' }" @click="selectedResolution = 'HD'">HD+</button>
              <button type="button" class="btn btn-outline-secondary btn-sm p-1" :class="{ active: selectedResolution === '4K' }" @click="selectedResolution = '4K'">4K+</button>
              <button type="button" class="btn btn-outline-secondary btn-sm p-1" :class="{ active: selectedResolution === '8K' }" @click="selectedResolution = '8K'">8K+</button>
            </div>
            <div class="position-relative">
              <label for="similarThreshold" class="label small">Similarity Threshold ({{ settings.similarThreshold }}%)</label>
              <input type="range" class="form-range" id="similarThreshold" v-model.number="settings.similarThreshold" min="0" max="100" step="1">
            </div>
            <div class="btn-group" role="group" aria-label="Filter by Duration">
              <button type="button" class="btn btn-outline-secondary btn-sm p-1" :class="{ active: selectedDuration === 0 }" @click="selectedDuration = 0">All&nbsp;Durations</button>
              <button type="button" class="btn btn-outline-secondary btn-sm p-1" :class="{ active: selectedDuration === 5 }" @click="selectedDuration = 5">+5min</button>
              <button type="button" class="btn btn-outline-secondary btn-sm p-1" :class="{ active: selectedDuration === 15 }" @click="selectedDuration = 15">+15min</button>
              <button type="button" class="btn btn-outline-secondary btn-sm p-1" :class="{ active: selectedDuration === 30 }" @click="selectedDuration = 30">+30min</button>
              <button type="button" class="btn btn-outline-secondary btn-sm p-1" :class="{ active: selectedDuration === 60 }" @click="selectedDuration = 60">+60min</button>
            </div>
          </div>

          <div class="form-floating mb-3 position-relative">
            <input id="filterInput" type="text" class="form-control pe-5"
                   placeholder="Filter files by Name..." v-model="filter">
            <label for="filterInput" class="text-muted">Filter files by Name...</label>
            <button v-if="filter" class="btn btn-outline-secondary bg-transparent border-0 position-absolute end-0 top-0 h-100" type="button" @click="filter = ''"><i class="bi bi-x"></i></button>
          </div>

          <div class="d-flex flex-column flex-lg-row justify-content-between mb-1 gap-2 align-items-center ">
            <div class="input-group-append ms-2 d-flex align-items-center">
              <label for="pageSize" class="me-1">Items per page</label>
              <select v-model="settings.pageSize" id="pageSize" class="form-select form-control w-auto ml-2">
                <option :value="4">4</option>
                <option :value="8">8</option>
                <option :value="12">12</option>
                <option :value="24">24</option>
                <option :value="0">All</option>
              </select>
            </div>
            <div class="form-check form-switch showVideoPreview">
              <input class="form-check-input" type="checkbox" id="videoPreviewSwitch" v-model="settings.showVideoPreview">
              <label class="form-check-label" for="videoPreviewSwitch">Show Video Preview</label>
            </div>
            <div class="btn-group ms-2" role="group" aria-label="Layout Switch">
              <button type="button" class="btn btn-outline-secondary btn-sm"
                      :class="{ active: settings.cardLayout }" @click="settings.cardLayout = true">
                <i class="bi bi-card-list"></i><span class="d-none d-lg-inline"> Card</span>
              </button>
              <button type="button" class="btn btn-outline-secondary btn-sm"
                      :class="{ active: !settings.cardLayout }" @click="settings.cardLayout = false">
                <i class="bi bi-list-ul"></i><span class="d-none d-lg-inline"> Detail</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
`

export const Filter = {
    template: template,
    props: {
        settings: {},
    },
    data() {
        return {
            filter: '',
            selectedFolder: '',
            selectedResolution: '',
            selectedDuration: 0,
            currentSort: 'created',
            currentSortDir: 'desc',
        };
    },
    computed: {
        uniqueFolders() {
            const folders = this.files.map(file => file.folder).filter(folder => folder);
            return [...new Set(folders)].sort();
        },
    },
    methods: {
        toggleFilterAccordion() {
            this.settings.filterAccordionOpen = !this.settings.filterAccordionOpen;
        },
    },
    mounted() {
    }
}