import { dbAdmin } from '../src/utils/firebase/admin';

async function listCollections() {
  const collections = await dbAdmin.listCollections();
  console.log('Existing Collections:', collections.map(c => c.id));
  process.exit(0);
}

listCollections().catch(err => {
  console.error(err);
  process.exit(1);
});
