import {showToast, handleViewChange} from "helper";
import { sharedState, settings } from "shared-state";

// language=Vue
const template = `
    <h3 class="mt-4">A Mosaic View of all videos</h3>

    <hs-loading v-if="sharedState.loading"></hs-loading>
    <div v-else>
        <div class="container mt-4">
            <div class="row row-cols-1 row-cols-sm-2 row-cols-md-3 g-4">
                <div class="col" v-for="file in sharedState.files" :key="file.url">
                    <div class="card" @click="toFile(file)">
                        <img :src="file.thumbnail" :alt="file.title" class="card-img-top mosaic">
                    </div>
                </div>
            </div>
        </div>
    </div>
`

export const Mosaic = {
    template: template,
    setup() {
        return { sharedState, settings };
    },
    data() {
        return {

        }
    },
    methods: {
        toFile(file) {
            if (file.title) {
                showToast(file.title, { title: 'Filter File' });
                sharedState.filter = file.title;
                settings.filterAccordionOpen = true;
                handleViewChange('')
            } else {
                showToast("File not found", { title: 'Not Found' });
            }
        }
    },
    mounted() {
    }
}