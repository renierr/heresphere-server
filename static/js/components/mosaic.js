import {showToast} from "helper";
import { sharedState, settings } from "shared-state";

// language=Vue
const template = `
    <h3 class="mt-4">A Mosaic View of all videos</h3>

    <hs-loading v-if="sharedState.loading"></hs-loading>
    <div v-else>
        <div class="container mt-4">
            <div class="row row-cols-1 row-cols-sm-2 row-cols-md-3 g-4">
                <div class="col" v-for="file in sharedState.files" :key="file.url">
                    <div class="card">
                        <img :src="file.thumbnail" :alt="file.title" class="card-img-top mosaic">
                    </div>
                </div>
            </div>
        </div>
    </div>

    <footer class="footer py-3">
        <div class="text-center mt-4">
            <div class="d-grid gap-2 d-sm-flex justify-content-sm-center">
              
            </div>
        </div>
    </footer>
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
    },
    mounted() {
    }
}